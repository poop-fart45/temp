from django.db import models


class Supplier(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Quote(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='quotes')
    quote_number = models.CharField(max_length=100)
    quote_date = models.DateField()
    pdf_file = models.FileField(upload_to='quotes/')
    processed_pdf = models.FileField(upload_to='processed_quotes/', null=True, blank=True)
    docx_file = models.FileField(upload_to='quotes_docx/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['supplier', 'quote_number']

    def __str__(self):
        return f"{self.supplier.name} - {self.quote_number}"


class QuoteItem(models.Model):
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name='items')
    item_number = models.CharField(max_length=100)
    description = models.TextField()
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    unit_of_measure = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['quote', 'item_number']

    def __str__(self):
        return f"{self.quote.quote_number} - {self.item_number}"


class PriceHistory(models.Model):
    quote_item = models.ForeignKey(QuoteItem, on_delete=models.CASCADE, related_name='price_history')
    business_unit = models.CharField(max_length=50)  # A, B, or C
    historical_price = models.DecimalField(max_digits=10, decimal_places=2)
    purchase_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Price histories'

    def __str__(self):
        return f"{self.quote_item.item_number} - {self.business_unit} - {self.purchase_date}"
