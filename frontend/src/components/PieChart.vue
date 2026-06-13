<template>
  <div class="chart-container" style="position: relative; height: 300px; width: 100%;">
    <Pie :data="chartData" :options="options" />
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
    options() {
      return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              color: '#9CA3AF', // slate-400
              font: {
                family: 'Outfit, sans-serif',
                size: 12
              }
            }
          },
          tooltip: {
            padding: 12,
            backgroundColor: '#1F2937', // gray-800
            titleColor: '#F3F4F6', // gray-100
            bodyColor: '#F3F4F6',
            bodyFont: {
              family: 'Outfit, sans-serif'
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
