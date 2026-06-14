import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import PieChart from '../../src/components/PieChart.vue';
import BarChart from '../../src/components/BarChart.vue';

describe('PieChart.vue', () => {
  const sampleData = {
    labels: ['식비', '교통비', '미분류'],
    datasets: [
      {
        backgroundColor: ['#10B981', '#3B82F6', '#6B7280'],
        data: [200000, 50000, 50000]
      }
    ]
  };

  it('Props로 전달받은 카테고리별 차트 데이터를 정상적으로 바인딩하여 차트 래퍼 요소를 렌더링한다', () => {
    const wrapper = mount(PieChart, {
      props: {
        chartData: sampleData
      }
    });

    // 1. 차트 렌더링 캔버스 또는 컨테이너 존재 여부 확인
    const canvas = wrapper.find('canvas');
    expect(canvas.exists()).toBe(true);
  });
});

describe('BarChart.vue', () => {
  const sampleData = {
    labels: ['2026-04', '2026-05', '2026-06'],
    datasets: [
      {
        label: '월별 지출액',
        backgroundColor: '#3B82F6',
        data: [850000, 920000, 300000]
      }
    ]
  };

  it('Props로 전달받은 최근 월별 지출 흐름 차트 데이터를 바인딩하여 막대 차트 캔버스를 렌더링한다', () => {
    const wrapper = mount(BarChart, {
      props: {
        chartData: sampleData
      }
    });

    const canvas = wrapper.find('canvas');
    expect(canvas.exists()).toBe(true);
  });
});
