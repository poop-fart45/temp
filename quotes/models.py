from django.db import models
from django.db.models import QuerySet
from typing import Optional
from datetime import date


class GPTPromptConfig(models.Model):
    """Configuration for GPT extraction prompts."""
    name = models.CharField(max_length=100, unique=True)
    system_prompt = models.TextField(
        help_text="System prompt for GPT extraction. Use {format_instructions} as placeholder for format instructions."
    )
    user_prompt = models.TextField(
        default="Please extract the quote information from the following text:\n\n{text_content}",
        help_text="User prompt for GPT extraction. Use {text_content} as placeholder for the quote text."
    )
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "GPT Prompt Configuration"
        verbose_name_plural = "GPT Prompt Configurations"

    def __str__(self):
        return f"{self.name} ({'active' if self.is_active else 'inactive'})"

    def save(self, *args, **kwargs):
        # Ensure only one config is active at a time
        if self.is_active:
            GPTPromptConfig.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs) 


class FredAero(models.Model):
    """
    Unmanaged model representing the FRED Aerospace index data.
    Records are monthly observations on the first of each month.
    """
    id = models.AutoField(primary_key=True)
    observation_date = models.DateField(db_column='observation_date', null=True)
    index_value = models.DecimalField(db_column='series_index', max_digits=7, decimal_places=3, null=True)

    class Meta:
        db_table = 'FRED_AERO'
        managed = False
        ordering = ['-observation_date']    # most recent dates first
        indexes = [
            models.Index(fields=['observation_date']),
        ]

    def __str__(self) -> str:
        return f"FRED Aero Index: {self.index_value} ({self.observation_date})"

    @staticmethod
    def _get_first_of_month(target_date: date) -> date:
        """
        Convert any date to the first of that month.
        
        Args:
            target_date: Any date
            
        Returns:
            Date object for the first of that month
        """
        return date(target_date.year, target_date.month, 1)

    @classmethod
    def get_index_for_date(cls, target_date: date) -> Optional['FredAero']:
        """
        Get the index value for any date by finding the most recent first-of-month
        observation on or before the target date.

        Args:
            target_date: The date to get the index value for

        Returns:
            FredAero instance or None if no data is available
        """
        # Get first of the month for target date
        first_of_month = cls._get_first_of_month(target_date)
        
        return cls.objects.filter(
            observation_date__lte=first_of_month
        ).order_by('-observation_date').first()

    @classmethod
    def get_index_range_for_analysis(
        cls, 
        start_date: date, 
        end_date: date = None,
    ) -> Optional[QuerySet]:
        """
        Get index values for a date range.
        Handles date alignment to first-of-month.

        Args:
            start_date: Start of the date range
            end_date: End of the date range (defaults to today)

        Returns:
            QuerySet of FredAero instances
        """
        # Default end_date to today if not provided
        end_date = end_date or date.today()
        
        # Align dates to first of month
        start_month = cls._get_first_of_month(start_date)
        end_month = cls._get_first_of_month(end_date)
        
        # Get the data
        queryset = cls.objects.filter(
            observation_date__gte=start_month,
            observation_date__lte=end_month
        ).order_by('observation_date')        
        return queryset
