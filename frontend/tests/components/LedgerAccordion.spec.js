import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import LedgerAccordion from '../../src/components/LedgerAccordion.vue';

describe('LedgerAccordion.vue', () => {
  const mockItems = [
    { item_name: '아이스 아메리카노', quantity: 2, unit_price: '4500.00' },
    { item_name: '클래식 스콘', quantity: 1, unit_price: '4500.00' }
  ];
  const mockVrn = '1208112345';

  it('props로 전달된 items와 사업자등록번호를 테이블에 올바르게 렌더링한다', () => {
    const wrapper = mount(LedgerAccordion, {
      props: {
        items: mockItems,
        vendorRegistrationNumber: mockVrn,
        isOpen: true
      }
    });

    // 1. 포맷팅된 사업자등록번호 (120-81-12345) 검증
    expect(wrapper.text()).toContain('120-81-12345');

    // 2. 테이블 품목 렌더링 검증
    expect(wrapper.text()).toContain('아이스 아메리카노');
    expect(wrapper.text()).toContain('2');
    expect(wrapper.text()).toContain('4,500'); // 천단위 콤마 포맷팅 검증

    expect(wrapper.text()).toContain('클래식 스콘');
    expect(wrapper.text()).toContain('1');
    expect(wrapper.text()).toContain('4,500');
  });

  it('isOpen이 false일 때 아코디언 컨테이너가 접힌 상태(높이 0)의 클래스를 가진다', () => {
    const wrapper = mount(LedgerAccordion, {
      props: {
        items: mockItems,
        vendorRegistrationNumber: mockVrn,
        isOpen: false
      }
    });

    const container = wrapper.find('.accordion-content');
    // max-h-0 클래스 또는 트랜지션 축소 스타일 클래스가 존재하는지 확인
    expect(container.classes()).toContain('max-h-0');
    expect(container.classes()).toContain('opacity-0');
  });

  it('isOpen이 true일 때 아코디언 컨테이너가 펼쳐진 상태의 클래스를 가진다', () => {
    const wrapper = mount(LedgerAccordion, {
      props: {
        items: mockItems,
        vendorRegistrationNumber: mockVrn,
        isOpen: true
      }
    });

    const container = wrapper.find('.accordion-content');
    expect(container.classes()).not.toContain('max-h-0');
    expect(container.classes()).toContain('max-h-[1000px]');
    expect(container.classes()).toContain('opacity-100');
  });
});
