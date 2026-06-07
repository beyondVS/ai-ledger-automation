import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import LedgerDeleteModal from '../../src/components/LedgerDeleteModal.vue';
import * as ledgerService from '../../src/services/ledgerService';

// API 모듈 Mocking
vi.mock('../../src/services/ledgerService', () => ({
  deleteLedgerEntry: vi.fn(),
  updateLedgerEntry: vi.fn(),
}));

describe('LedgerDeleteModal.vue', () => {
  const mockLedger = {
    id: '01944e8d-88f5-7c1c-9226-eb52c6f1a8e1',
    vendor_name: '스타벅스 강남점',
    total_amount: '15000.00',
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('isOpen이 false일 때 삭제 모달이 노출되지 않아야 한다', () => {
    const wrapper = mount(LedgerDeleteModal, {
      props: {
        isOpen: false,
        ledger: mockLedger,
      },
    });
    expect(wrapper.find('.delete-modal-backdrop').exists()).toBe(false);
  });

  it('isOpen이 true일 때 가맹점명 및 경고 메시지가 화면에 노출된다', () => {
    const wrapper = mount(LedgerDeleteModal, {
      props: {
        isOpen: true,
        ledger: mockLedger,
      },
    });

    // 경고 영역 렌더링 확인
    expect(wrapper.text()).toContain('스타벅스 강남점');
    expect(wrapper.text()).toContain('정말 삭제하시겠습니까');
  });

  it('취소 버튼을 클릭하면 API 호출 없이 close 이벤트를 발생시킨다', async () => {
    const wrapper = mount(LedgerDeleteModal, {
      props: {
        isOpen: true,
        ledger: mockLedger,
      },
    });

    const cancelButton = wrapper.find('.btn-cancel');
    await cancelButton.trigger('click');

    expect(ledgerService.deleteLedgerEntry).not.toHaveBeenCalled();
    expect(wrapper.emitted().close).toBeTruthy();
  });

  it('확인 버튼을 클릭하면 deleteLedgerEntry API가 호출되고 confirm 및 close 이벤트를 발생시킨다', async () => {
    ledgerService.deleteLedgerEntry.mockResolvedValue();

    const wrapper = mount(LedgerDeleteModal, {
      props: {
        isOpen: true,
        ledger: mockLedger,
      },
    });

    const confirmButton = wrapper.find('.btn-confirm');
    await confirmButton.trigger('click');

    expect(ledgerService.deleteLedgerEntry).toHaveBeenCalledWith(mockLedger.id);

    // 비동기 갱신 대기
    await wrapper.vm.$nextTick();
    await new Promise((resolve) => setTimeout(resolve, 10));

    expect(wrapper.emitted().confirm).toBeTruthy();
    expect(wrapper.emitted().close).toBeTruthy();
  });
});
