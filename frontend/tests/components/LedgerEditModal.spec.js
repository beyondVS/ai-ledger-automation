import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import LedgerEditModal from '../../src/components/LedgerEditModal.vue';
import * as ledgerService from '../../src/services/ledgerService';

// ledgerService API 모듈 Mocking
vi.mock('../../src/services/ledgerService', () => ({
  updateLedgerEntry: vi.fn(),
  deleteLedgerEntry: vi.fn(), // US2/T016 호환용
}));

describe('LedgerEditModal.vue', () => {
  const mockLedger = {
    id: '01944e8d-88f5-7c1c-9226-eb52c6f1a8e1',
    vendor_name: '스타벅스 강남점',
    transaction_date: '2026-06-07T00:00:00Z',
    total_amount: '15000.00',
    category: '미분류',
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('isOpen이 false일 때 모달 백드롭이 렌더링되지 않거나 보이지 않아야 한다', () => {
    const wrapper = mount(LedgerEditModal, {
      props: {
        isOpen: false,
        ledger: mockLedger,
      },
    });
    expect(wrapper.find('.modal-backdrop').exists()).toBe(false);
  });

  it('isOpen이 true일 때 폼 입력 필드가 props로 전달된 ledger 데이터로 초기화되어 렌더링된다', () => {
    const wrapper = mount(LedgerEditModal, {
      props: {
        isOpen: true,
        ledger: mockLedger,
      },
    });

    expect(wrapper.find('input[id="vendor_name"]').element.value).toBe('스타벅스 강남점');
    expect(wrapper.find('input[id="transaction_date"]').element.value).toBe('2026-06-07T00:00');
    expect(wrapper.find('input[id="total_amount"]').element.value).toBe('15000.00');
    expect(wrapper.find('select[id="category"]').element.value).toBe('미분류');
  });

  it('가맹점명을 공백으로 입력하면 유효성 에러 메시지를 보여주고 API를 호출하지 않는다', async () => {
    const wrapper = mount(LedgerEditModal, {
      props: {
        isOpen: true,
        ledger: mockLedger,
      },
    });

    const vendorNameInput = wrapper.find('input[id="vendor_name"]');
    await vendorNameInput.setValue('');

    // 저장 버튼 클릭 시도
    await wrapper.find('form').trigger('submit.prevent');

    // 경고 메시지 노출 확인 (화면에 에러 클래스 또는 에러 메시지 텍스트 존재 확인)
    expect(wrapper.text()).toContain('가맹점명을 입력해주세요');
    expect(ledgerService.updateLedgerEntry).not.toHaveBeenCalled();
  });

  it('유효한 값을 입력하고 저장 버튼을 누르면 updateLedgerEntry API가 호출되고 save 및 close 이벤트를 발생시킨다', async () => {
    ledgerService.updateLedgerEntry.mockResolvedValue({
      ...mockLedger,
      vendor_name: '스타벅스 신사점',
      category: '식비',
    });

    const wrapper = mount(LedgerEditModal, {
      props: {
        isOpen: true,
        ledger: mockLedger,
      },
    });

    await wrapper.find('input[id="vendor_name"]').setValue('스타벅스 신사점');
    await wrapper.find('select[id="category"]').setValue('식비');

    await wrapper.find('form').trigger('submit.prevent');

    // API가 적절한 인자로 호출되었는지 확인
    expect(ledgerService.updateLedgerEntry).toHaveBeenCalledWith(mockLedger.id, {
      vendor_name: '스타벅스 신사점',
      transaction_date: '2026-06-07T00:00:00Z',
      total_amount: '15000.00',
      category: '식비',
    });

    // 비동기 갱신 대기
    await wrapper.vm.$nextTick();
    await new Promise((resolve) => setTimeout(resolve, 10));

    // save 및 close 이벤트 emit 여부 검증
    expect(wrapper.emitted().save).toBeTruthy();
    expect(wrapper.emitted().close).toBeTruthy();
  });
});
