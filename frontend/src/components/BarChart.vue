<template>
  <div class="chart-container" style="position: relative; height: 300px; width: 100%;">
    <Bar :data="processedChartData" :options="options" />
  </div>
</template>

<script>
import { Bar } from 'vue-chartjs';
import { Chart as ChartJS, Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale } from 'chart.js';

ChartJS.register(Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale);

export default {
  name: 'BarChart',
  components: { Bar },
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
      
      const datasets = this.chartData.datasets.map(ds => {
        return {
          ...ds,
          backgroundColor: (context) => {
            const chart = context.chart;
            const { ctx, chartArea } = chart;
            if (!chartArea) return 'rgba(79, 70, 229, 0.8)';
            const gradient = ctx.createLinearGradient(0, chartArea.bottom, 0, chartArea.top);
            gradient.addColorStop(0, 'rgba(79, 70, 229, 0.35)'); // Indigo-600
            gradient.addColorStop(1, 'rgba(16, 185, 129, 0.85)'); // Emerald-500
            return gradient;
          },
          hoverBackgroundColor: (context) => {
            const chart = context.chart;
            const { ctx, chartArea } = chart;
            if (!chartArea) return 'rgba(79, 70, 229, 1)';
            const gradient = ctx.createLinearGradient(0, chartArea.bottom, 0, chartArea.top);
            gradient.addColorStop(0, 'rgba(79, 70, 229, 0.65)');
            gradient.addColorStop(1, 'rgba(16, 185, 129, 1)');
            return gradient;
          },
          borderRadius: 8,
          borderSkipped: false
        };
      });
      
      return {
        ...this.chartData,
        datasets
      };
    },
    options() {
      const isDark = document.documentElement.classList.contains('dark');
      const textColor = isDark ? '#9CA3AF' : '#4B5563'; // dark: slate-400, light: slate-600
      const gridColor = isDark ? 'rgba(75, 85, 99, 0.15)' : 'rgba(209, 213, 219, 0.4)';
      const tooltipBg = isDark ? '#1F2937' : '#FFFFFF';
      const tooltipText = isDark ? '#F3F4F6' : '#1F2937';
      const tooltipBorder = isDark ? '#374151' : '#E5E7EB';

      return {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            grid: {
              display: false
            },
            ticks: {
              color: textColor,
              font: {
                family: 'Outfit, var(--font-pretendard), sans-serif',
                size: 11
              }
            }
          },
          y: {
            grid: {
              color: gridColor
            },
            ticks: {
              color: textColor,
              font: {
                family: 'Outfit, var(--font-pretendard), sans-serif',
                size: 11
              },
              callback: function(value) {
                return (value / 10000).toLocaleString();
              }
            }
          }
        },
        plugins: {
          legend: {
            display: false
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
                let label = context.dataset.label || '';
                if (label) {
                  label += ': ';
                }
                if (context.parsed.y !== undefined) {
                  label += new Intl.NumberFormat('ko-KR', { style: 'currency', currency: 'KRW' }).format(context.parsed.y);
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
