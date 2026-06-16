import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import LedgerEditModal from "../../src/components/LedgerEditModal.vue";

describe("Receipt Camera Capture Fallback Validation", () => {
  it("영수증 첨부 input 엘리먼트는 accept가 image/*이고 capture 속성이 environment로 설정되어야 한다", () => {
    // LedgerEditModal 기동 시 요구되는 기초 Props 설정 모킹
    const wrapper = mount(LedgerEditModal, {
      props: {
        isOpen: true,
        ledger: {
          id: 1,
          merchant: "테스트 가맹점",
          amount: 10000,
          payment_date: "2026-06-17T00:00"
        }
      }
    });

    const fileInput = wrapper.find('[data-testid="receipt-input"]');
    expect(fileInput.exists()).toBe(true);
    expect(fileInput.attributes("accept")).toContain("image/*");
    // 모바일 후면 카메라 자동 다이렉트 캡처 스펙 검증
    expect(fileInput.attributes("capture")).toBe("environment");
  });
});
