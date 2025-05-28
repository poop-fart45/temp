from typing import Dict, List
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from django.db import connections
from datetime import datetime, timedelta, date
from quotes.models import FredAero


class PriceAnalyzer:
    def __init__(self):
        self.business_units = ['business_unit_a', 'business_unit_b', 'business_unit_c']
        
    def fetch_historical_prices(self, item_number: str, lookback_days: int = 365) -> pd.DataFrame:
        """
        Fetch historical prices for an item from all business units.
        Returns a DataFrame with columns: business_unit, price, purchase_date
        """
        cutoff_date = datetime.now() - timedelta(days=lookback_days)
        all_data = []

        for unit in self.business_units:
            with connections[unit].cursor() as cursor:
                # This is a placeholder query - adjust according to actual database schema
                query = """
                    SELECT 
                        price,
                        purchase_date
                    FROM historical_purchases
                    WHERE item_number = %s
                    AND purchase_date >= %s
                    ORDER BY purchase_date DESC
                """
                cursor.execute(query, [item_number, cutoff_date])
                rows = cursor.fetchall()
                
                unit_data = pd.DataFrame(rows, columns=['price', 'purchase_date'])
                unit_data['business_unit'] = unit
                all_data.append(unit_data)

        if not all_data:
            return pd.DataFrame(columns=['business_unit', 'price', 'purchase_date'])
            
        return pd.concat(all_data, ignore_index=True)

    def _normalize_series(self, data: pd.Series) -> pd.Series:
        """Normalize a series to percentage change from first value."""
        if data.empty:
            return pd.Series()
        first_value = data.iloc[0]
        if first_value == 0:
            return pd.Series([0] * len(data))
        return ((data - first_value) / first_value) * 100

    def _add_change_annotation(self, ax, data: pd.Series, y_offset: float = 5):
        """Add total change annotation to the plot."""
        if len(data) < 2:
            return
        
        total_change = data.iloc[-1] - data.iloc[0]
        color = 'green' if total_change >= 0 else 'red'
        ax.annotate(
            f'{total_change:+.1f}%',
            xy=(data.index[-1], data.iloc[-1]),
            xytext=(10, y_offset),
            textcoords='offset points',
            color=color,
            weight='bold'
        )

    def generate_price_trend_plot(self, data: pd.DataFrame, item_number: str) -> str:
        """
        Generate a price trend plot using Seaborn, showing normalized price changes
        and aerospace index changes on the same scale.
        Returns the path to the saved plot image.
        """
        if data.empty:
            return None

        # Sort data by date and get date range
        data = data.sort_values('purchase_date')
        start_date = data['purchase_date'].min()
        end_date = data['purchase_date'].max()

        # Get index data for the same period
        index_data = FredAero.get_index_range_for_analysis(
            start_date=start_date.date() if isinstance(start_date, datetime) else start_date,
            end_date=end_date.date() if isinstance(end_date, datetime) else end_date
        )
        if not index_data.exists():
            return self._generate_basic_price_plot(data, item_number)

        # Convert index data to DataFrame
        index_df = pd.DataFrame(
            index_data.values('observation_date', 'index_value')
        ).rename(columns={
            'observation_date': 'date',
            'index_value': 'series_index'  # Match the db_column name
        })

        if index_df.empty:
            return self._generate_basic_price_plot(data, item_number)

        # Create the plot
        sns.set_style("whitegrid")
        fig, ax1 = plt.subplots(figsize=(12, 6))

        # Plot normalized price changes as scatter points
        for unit in data['business_unit'].unique():
            unit_data = data[data['business_unit'] == unit]
            if not unit_data.empty:
                normalized_prices = self._normalize_series(unit_data['price'])
                if not normalized_prices.empty:
                    ax1.scatter(
                        unit_data['purchase_date'],
                        normalized_prices,
                        label=f'{unit} (Price)',
                        alpha=0.6,
                        s=50
                    )
                    # Add change annotation for each business unit
                    self._add_change_annotation(ax1, normalized_prices, y_offset=5 * (list(data['business_unit'].unique()).index(unit) + 1))

        # Plot normalized index as a line
        normalized_index = self._normalize_series(index_df['series_index'])
        if not normalized_index.empty:
            ax1.plot(
                index_df['date'],
                normalized_index,
                color='red',
                label='Aerospace Index',
                alpha=0.8,
                linewidth=2
            )
            # Add change annotation for index
            self._add_change_annotation(ax1, normalized_index, y_offset=-15)

        # Customize the plot
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Percentage Change from Initial Value (%)')
        plt.title(f'Normalized Price Trends vs Aerospace Index - Item {item_number}')
        
        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45)
        
        # Add legend with a better position that doesn't overlap the plot
        plt.legend(loc='center left', bbox_to_anchor=(1.05, 0.5))
        
        # Save plot to a temporary file
        plot_path = f'media/plots/price_trend_{item_number}.png'
        plt.savefig(plot_path, bbox_inches='tight', dpi=300)  # Higher DPI for better quality
        plt.close(fig)  # Be specific about which figure to close

        return plot_path

    def _generate_basic_price_plot(self, data: pd.DataFrame, item_number: str) -> str:
        """Generate a basic price plot when index data is not available."""
        sns.set_style("whitegrid")
        fig, ax = plt.subplots(figsize=(10, 6))
        
        sns.scatterplot(
            data=data,
            x='purchase_date',
            y='price',
            hue='business_unit',
            alpha=0.6,
            s=50,
            ax=ax
        )

        plt.title(f'Historical Price Trends - Item {item_number}')
        ax.set_xlabel('Purchase Date')
        ax.set_ylabel('Price')
        plt.xticks(rotation=45)
        
        # Save plot to a temporary file
        plot_path = f'media/plots/price_trend_{item_number}.png'
        plt.savefig(plot_path, bbox_inches='tight', dpi=300)  # Higher DPI for better quality
        plt.close(fig)  # Be specific about which figure to close

        return plot_path

    def calculate_price_statistics(self, data: pd.DataFrame) -> Dict:
        """Calculate price statistics for the item."""
        if data.empty:
            return {
                'min_price': None,
                'max_price': None,
                'avg_price': None,
                'price_volatility': None,
                'recent_trend': None
            }

        stats = {
            'min_price': float(data['price'].min()),
            'max_price': float(data['price'].max()),
            'avg_price': float(data['price'].mean()),
            'price_volatility': float(data['price'].std()),
        }

        # Calculate recent trend (last 90 days vs previous 90 days)
        recent_data = data[data['purchase_date'] >= datetime.now() - timedelta(days=90)]
        previous_data = data[
            (data['purchase_date'] < datetime.now() - timedelta(days=90)) &
            (data['purchase_date'] >= datetime.now() - timedelta(days=180))
        ]

        if not recent_data.empty and not previous_data.empty:
            recent_avg = recent_data['price'].mean()
            previous_avg = previous_data['price'].mean()
            stats['recent_trend'] = float((recent_avg - previous_avg) / previous_avg * 100)
        else:
            stats['recent_trend'] = None

        return stats

    def analyze_item_prices(self, item_number: str, lookback_days: int = 365) -> Dict:
        """
        Perform complete price analysis for an item.
        Returns both statistical data and plot path.
        """
        historical_data = self.fetch_historical_prices(item_number, lookback_days)
        
        if historical_data.empty:
            return {
                'statistics': self.calculate_price_statistics(historical_data),
                'plot_path': None,
                'has_data': False
            }

        plot_path = self.generate_price_trend_plot(historical_data, item_number)
        
        return {
            'statistics': self.calculate_price_statistics(historical_data),
            'plot_path': plot_path,
            'has_data': True
        } 