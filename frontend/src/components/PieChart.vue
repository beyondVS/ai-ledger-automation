<template>
  <div class="chart-container" style="position: relative; height: 300px; width: 100%;">
    <Pie :data="processedChartData" :options="options" />
  </div>
</template>

<script>
import { Pie } from 'vue-chartjs';
import { Chart as ChartJS, Title, Tooltip, Legend, ArcElement, CategoryScale } from 'chart.js';

ChartJS.register(Title, Tooltip, Legend, ArcElement, CategoryScale);

export default {
  name: 'PieChart',
  components: { Pie },
  props: {
    chartData: {
      type: Object,
      required: true
    },
    chartOptions: {
      type: Object,
      default: () => ({})
    }
  },
  computed: {
    processedChartData() {
      if (!this.chartData || !this.chartData.datasets || !this.chartData.datasets[0]) {
        return this.chartData;
      }
      const data = this.chartData.datasets[0].data || [];
      const total = data.reduce((sum, val) => sum + val, 0);
      
      const newLabels = (this.chartData.labels || []).map((label, index) => {
        const val = data[index] || 0;
        const percentage = total > 0 ? ((val / total) * 100).toFixed(1) : 0;
        return `${label} (${percentage}%)`;
      });
      
      return {
        ...this.chartData,
        labels: newLabels
      };
    },
    options() {
      const isDark = document.documentElement.classList.contains('dark');
      const textColor = isDark ? '#9CA3AF' : '#4B5563'; // dark: slate-400, light: slate-600
      const tooltipBg = isDark ? '#1F2937' : '#FFFFFF';
      const tooltipText = isDark ? '#F3F4F6' : '#1F2937';
      const tooltipBorder = isDark ? '#374151' : '#E5E7EB';

      return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              color: textColor,
              font: {
                family: 'Outfit, var(--font-pretendard), sans-serif',
                size: 11
              }
            }
          },
          tooltip: {
            padding: 12,
            backgroundColor: tooltipBg,
            titleColor: tooltipText,
            bodyColor: tooltipText,
            borderColor: tooltipBorder,
            borderWidth: 1,
            bodyFont: {
              family: 'Outfit, var(--font-pretendard), sans-serif'
            },
            callbacks: {
              label: function(context) {
                let label = context.label || '';
                if (label) {
                  label += ': ';
                }
                if (context.parsed !== undefined) {
                  label += new Intl.NumberFormat('ko-KR', { style: 'currency', currency: 'KRW' }).format(context.parsed);
                }
                return label;
              }
            }
          }
        },
        ...this.chartOptions
      };
    }
  }
};
</script>
