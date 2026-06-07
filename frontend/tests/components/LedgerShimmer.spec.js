import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import LedgerShimmer from '../../src/components/LedgerShimmer.vue';

describe('LedgerShimmer.vue', () => {
  const mockJob = {
    id: 'job-uuid-1',
    status: 'PENDING',
    raw_file_name: 'receipt_2026_06_07.pdf'
  };

  it('job의 상태가 PENDING일 때 Shimmer 로더 스켈레톤 요소와 파일명을 정상적으로 렌더링한다', () => {
    const wrapper = mount(LedgerShimmer, {
      props: {
        job: mockJob
      }
    });

    // 1. 파일명 렌더링 확인
    expect(wrapper.text()).toContain('receipt_2026_06_07.pdf');
    // 2. 분석 대기 중 텍스트 확인
    expect(wrapper.text()).toContain('분석 대기 중');
    // 3. Shimmer 효과 클래스 (animate-pulse) 검증
    const pulseElements = wrapper.findAll('.shimmer-bar');
    expect(pulseElements.length).toBeGreaterThan(0);
    expect(pulseElements[0].classes()).toContain('animate-pulse');
  });

  it('job의 상태가 PROCESSING으로 변경되면 진행 중 상태 텍스트로 전환된다', () => {
    const wrapper = mount(LedgerShimmer, {
      props: {
        job: { ...mockJob, status: 'PROCESSING' }
      }
    });

    expect(wrapper.text()).toContain('AI 분석 진행 중');
  });
});
