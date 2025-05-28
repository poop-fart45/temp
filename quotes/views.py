from django.shortcuts import render
import os
from django.shortcuts import render, redirect
from django.http import FileResponse, Http404
from django.views import View
from django.contrib import messages
from django.conf import settings

from .models import Quote, Supplier
from .services.pdf_processor.processor import PDFProcessor
from .services.gpt_extractor.extractor import GPTExtractor
from .services.report_generator.generator import ReportGenerator


class QuoteUploadView(View):
    template_name = 'quotes/upload.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        if 'quote_file' not in request.FILES:
            messages.error(request, 'Please select a PDF file to upload.')
            return render(request, self.template_name)

        quote_file = request.FILES['quote_file']
        if not quote_file.name.lower().endswith('.pdf'):
            messages.error(request, 'Please upload a PDF file.')
            return render(request, self.template_name)

        try:
            # Save the uploaded file
            upload_path = os.path.join(settings.MEDIA_ROOT, 'uploads', quote_file.name)
            os.makedirs(os.path.dirname(upload_path), exist_ok=True)
            
            with open(upload_path, 'wb+') as destination:
                for chunk in quote_file.chunks():
                    destination.write(chunk)

            # Process the PDF
            pdf_processor = PDFProcessor(upload_path)
            text_content = pdf_processor.extract_text()

            # Extract structured data using GPT
            gpt_extractor = GPTExtractor()
            quote_data = gpt_extractor.extract_quote_data(text_content)

            # Save to database
            supplier, _ = Supplier.objects.get_or_create(name=quote_data.supplier_name)
            
            quote = Quote.objects.create(
                supplier=supplier,
                quote_number=quote_data.quote_number,
                quote_date=quote_data.quote_date,
                pdf_file=upload_path
            )

            # Generate reports
            report_generator = ReportGenerator(quote_data.dict())
            pdf_path = report_generator.generate_pdf()
            docx_path = report_generator.generate_docx()

            # Update quote with generated files
            quote.processed_pdf = pdf_path
            quote.docx_file = docx_path
            quote.save()

            # Store quote ID in session for retrieval
            request.session['last_quote_id'] = quote.id
            
            return redirect('quote_result')

        except Exception as e:
            messages.error(request, f'Error processing quote: {str(e)}')
            return render(request, self.template_name)


class QuoteResultView(View):
    template_name = 'quotes/result.html'

    def get(self, request):
        quote_id = request.session.get('last_quote_id')
        if not quote_id:
            messages.error(request, 'No quote found. Please upload a quote first.')
            return redirect('quote_upload')

        try:
            quote = Quote.objects.get(id=quote_id)
            return render(request, self.template_name, {'quote': quote})
        except Quote.DoesNotExist:
            messages.error(request, 'Quote not found.')
            return redirect('quote_upload')


class DownloadReportView(View):
    def get(self, request, quote_id, format='pdf'):
        try:
            quote = Quote.objects.get(id=quote_id)
            
            if format == 'pdf':
                file_path = quote.processed_pdf.path
                content_type = 'application/pdf'
            elif format == 'docx':
                file_path = quote.docx_file.path
                content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            else:
                raise Http404('Invalid format requested')

            response = FileResponse(open(file_path, 'rb'), content_type=content_type)
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
            return response

        except Quote.DoesNotExist:
            raise Http404('Quote not found')
        except Exception as e:
            messages.error(request, f'Error downloading file: {str(e)}')
            return redirect('quote_result')
