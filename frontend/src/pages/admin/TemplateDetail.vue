<template>
  <div class="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-10 font-sans">
    <div class="max-w-6xl mx-auto space-y-8">
      
      <!-- 상단 상호작용 바 및 타이틀 -->
      <div class="flex flex-col md:flex-row md:items-center md:justify-between space-y-4 md:space-y-0">
        <div class="flex items-center space-x-4">
          <router-link
            to="/admin/templates"
            class="inline-flex items-center justify-center p-2.5 bg-slate-900 border border-slate-800 rounded-xl text-slate-300 hover:text-white hover:bg-slate-800 hover:border-slate-700 transition"
          >
            ← 목록
          </router-link>
          <div>
            <h1 class="text-2xl font-extrabold tracking-tight text-slate-100 flex items-center space-x-3">
              <span>{{ template.vendor_name }}</span>
              <span v-if="template.is_blacklisted" class="px-2.5 py-0.5 rounded-full text-xs bg-rose-500/20 text-rose-400 border border-rose-500/30">
                🚫 블랙리스트
              </span>
              <span v-else-if="template.is_verified" class="px-2.5 py-0.5 rounded-full text-xs bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                ✓ 검증 완료
              </span>
              <span v-else class="px-2.5 py-0.5 rounded-full text-xs bg-amber-500/20 text-amber-400 border border-amber-500/30">
                ⏳ 자동 학습 중
              </span>
            </h1>
            <p class="text-xs text-slate-400 mt-1 font-mono">
              사업자등록번호: {{ formatBizNum(template.vendor_registration_number) }}
            </p>
          </div>
        </div>

        <!-- 제어 액션 그룹 -->
        <div class="flex items-center space-x-3">
          <!-- 자가치유 카운터 리셋 (블랙리스트 해제) -->
          <button
            v-if="template.is_blacklisted || template.self_healing_attempts > 0"
            @click="handleResetHealing"
            :disabled="actionLoading"
            class="px-4 py-2 border border-amber-500/40 rounded-xl text-sm font-semibold text-amber-400 hover:bg-amber-500/10 transition disabled:opacity-50"
          >
            🔄 치유 카운터 초기화
          </button>
          
          <!-- 수동 승격 및 정규식 조율 -->
          <button
            @click="openVerifyModal"
            :disabled="actionLoading"
            class="px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-bold rounded-xl text-sm transition shadow-lg shadow-emerald-500/15 disabled:opacity-50"
          >
            🛠️ 수동 정규식 조율 & 승격
          </button>
        </div>
      </div>

      <!-- 상단 정보 요약 카드 그리드 -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <!-- 템플릿 메타 정보 카드 -->
        <div class="bg-slate-900/40 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <h2 class="text-sm font-bold text-slate-400 uppercase tracking-wider">자가 치유 상태</h2>
          <div class="grid grid-cols-2 gap-4">
            <div class="bg-slate-950/60 p-4 border border-slate-800/60 rounded-xl text-center">
              <div class="text-xs text-slate-500">일관성 카운트</div>
              <div class="text-2xl font-black text-slate-200 mt-1 font-mono">{{ template.consistency_count }} / 3</div>
            </div>
            <div class="bg-slate-950/60 p-4 border border-slate-800/60 rounded-xl text-center">
              <div class="text-xs text-slate-500">자가치유 시도</div>
              <div class="text-2xl font-black text-slate-200 mt-1 font-mono">{{ template.self_healing_attempts }} / 3</div>
            </div>
          </div>
          <div class="text-xs text-slate-400">
            <span class="font-semibold">최근 자가 치유 일시: </span>
            <span class="font-mono">{{ formatDateTime(template.last_healing_at) }}</span>
          </div>
        </div>

        <!-- 현재 정규식 패턴 정보 카드 -->
        <div class="bg-slate-900/40 border border-slate-800 rounded-2xl p-6 shadow-xl md:col-span-2 space-y-4">
          <h2 class="text-sm font-bold text-slate-400 uppercase tracking-wider">현재 파싱 정규식 규칙</h2>
          <div class="space-y-3 font-mono text-xs text-slate-300">
            <div class="bg-slate-950 border border-slate-800 rounded-xl p-3.5 flex flex-col space-y-1">
              <span class="text-[10px] text-emerald-400 font-semibold uppercase">날짜 추출 정규식 (date_pattern)</span>
              <code class="text-slate-200 select-all overflow-x-auto whitespace-pre">{{ parsingRules.date_pattern || '정의되지 않음' }}</code>
            </div>
            <div class="bg-slate-950 border border-slate-800 rounded-xl p-3.5 flex flex-col space-y-1">
              <span class="text-[10px] text-emerald-400 font-semibold uppercase">금액 추출 정규식 (amount_pattern)</span>
              <code class="text-slate-200 select-all overflow-x-auto whitespace-pre">{{ parsingRules.amount_pattern || '정의되지 않음' }}</code>
            </div>
          </div>
        </div>
      </div>

      <!-- 실행 및 오류 히스토리 타임라인 -->
      <div class="bg-slate-900/20 border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-6">
        <h2 class="text-lg font-bold text-slate-200">📊 템플릿 실행 이력 및 자가치유 로그</h2>
        
        <div v-if="loadingHistory" class="flex flex-col items-center justify-center py-10 space-y-3">
          <div class="w-8 h-8 border-4 border-slate-800 border-t-emerald-500 rounded-full animate-spin"></div>
          <p class="text-slate-500 text-xs">히스토리를 불러오는 중입니다...</p>
        </div>

        <div v-else-if="history.length === 0" class="text-center py-12 text-slate-500">
          실행 이력이 존재하지 않습니다.
        </div>

        <div v-else class="space-y-6">
          <div v-for="item in history" :key="item.id" class="bg-slate-900 border border-slate-800/80 rounded-xl p-5 hover:border-slate-700 transition duration-200 space-y-4">
            <!-- 히스토리 탑 뱃지 바 -->
            <div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/60 pb-3">
              <div class="flex items-center space-x-3">
                <span :class="item.parsing_mode === 'BYPASS' ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' : 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30'" class="px-2.5 py-0.5 rounded-lg text-xs font-bold border font-mono">
                  {{ item.parsing_mode }}
                </span>
                <span :class="item.is_success ? 'text-emerald-400' : 'text-rose-400'" class="text-xs font-semibold">
                  {{ item.is_success ? '✓ 파싱 성공' : '✗ 파싱 에러' }}
                </span>
              </div>
              <div class="text-xs text-slate-400 font-mono">
                {{ formatDateTime(item.execution_time) }}
              </div>
            </div>

            <!-- 에러 메시지 렌더링 -->
            <div v-if="item.error_message" class="bg-rose-500/10 border border-rose-500/20 rounded-xl p-4 text-sm text-rose-300 font-mono">
              <div class="text-[10px] text-rose-400 font-bold uppercase tracking-wider mb-1">Error Message</div>
              {{ item.error_message }}
            </div>

            <!-- 사용자 수동 정정 Diff 렌더링 -->
            <div v-if="item.user_corrected && item.corrected_diff" class="space-y-2">
              <div class="text-xs font-bold text-slate-400 uppercase tracking-wider">✍️ 사용자 수동 정정 내역 (Diff)</div>
              
              <div class="grid grid-cols-1 gap-3 font-mono text-xs">
                <div v-for="(diff, index) in item.corrected_diff" :key="index" class="bg-slate-950 border border-slate-800 rounded-xl overflow-hidden">
                  <div class="bg-slate-900 px-4 py-2 border-b border-slate-800 text-[10px] font-bold text-slate-400 uppercase">
                    수정 필드: {{ diff.field }}
                  </div>
                  <div class="grid grid-cols-2 divide-x divide-slate-800/80">
                    <div class="p-3 bg-rose-500/10 text-rose-300">
                      <div class="text-[9px] text-rose-400 uppercase tracking-widest mb-1">Before</div>
                      {{ formatDiffValue(diff.field, diff.before) }}
                    </div>
                    <div class="p-3 bg-emerald-500/10 text-emerald-300">
                      <div class="text-[9px] text-emerald-400 uppercase tracking-widest mb-1">After</div>
                      {{ formatDiffValue(diff.field, diff.after) }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 수동 정규식 조율 모달 (Modal) -->
      <div v-if="showVerifyModal" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
        <div class="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-6 transform scale-100 transition-all duration-300">
          <div class="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 class="text-lg font-bold text-slate-100">🛠️ 수동 정규식 조율 및 템플릿 승격</h3>
            <button @click="closeVerifyModal" class="text-slate-400 hover:text-white transition text-lg">&times;</button>
          </div>

          <div class="space-y-4">
            <p class="text-xs text-slate-400 leading-relaxed">
              정규식 패턴을 수동으로 편집하여 템플릿을 강제 승인(is_verified: true)시킵니다. 승격이 성공하면 즉시 LLM API 우회가 가동됩니다.
            </p>

            <div class="space-y-3 font-mono text-xs">
              <div class="flex flex-col space-y-1.5">
                <label class="text-[10px] text-slate-400 font-bold uppercase tracking-wider">날짜 추출 정규식 (date_pattern)</label>
                <input
                  type="text"
                  v-model="editRules.date_pattern"
                  class="bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-200 focus:outline-none focus:border-emerald-500 transition font-mono"
                />
              </div>

              <div class="flex flex-col space-y-1.5">
                <label class="text-[10px] text-slate-400 font-bold uppercase tracking-wider">금액 추출 정규식 (amount_pattern)</label>
                <input
                  type="text"
                  v-model="editRules.amount_pattern"
                  class="bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-200 focus:outline-none focus:border-emerald-500 transition font-mono"
                />
              </div>
            </div>
          </div>

          <div class="flex items-center justify-end space-x-3 border-t border-slate-800 pt-4">
            <button
              @click="closeVerifyModal"
              class="px-4 py-2 border border-slate-700 hover:bg-slate-800 text-slate-300 font-semibold rounded-xl text-sm transition"
            >
              취소
            </button>
            <button
              @click="handleVerify"
              :disabled="actionLoading"
              class="px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-extrabold rounded-xl text-sm transition disabled:opacity-50"
            >
              승격 완료
            </button>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script>
import { getTemplates, getTemplateHistory, verifyTemplate, resetHealing } from '../../services/adminService';

export default {
  name: 'TemplateDetail',
  data() {
    return {
      templateId: this.$route.params.id,
      template: {},
      parsingRules: {},
      history: [],
      loadingHistory: false,
      actionLoading: false,
      showVerifyModal: false,
      editRules: {
        date_pattern: '',
        amount_pattern: ''
      }
    };
  },
  mounted() {
    this.fetchTemplateDetails();
    this.fetchHistory();
  },
  methods: {
    // 템플릿 메타 정보 조회 (목록 조회 API에서 특정 템플릿만 추출)
    async fetchTemplateDetails() {
      try {
        const response = await getTemplates({ id: this.templateId });
        // results 배열에서 일치하는 template 추출
        const found = response.results.find(t => t.id === this.templateId);
        if (found) {
          this.template = found;
          // 백엔드 API에서 제공되는 parsing_rules를 가져오기 위해 verify용 초기 폼 바인딩 대기
          // (목록 API에서는 parsing_rules가 없을 수 있으므로 verify를 위한 template detail을 확보)
          // parsingRules 기본값 주입
          this.parsingRules = found.parsing_rules || {
            date_pattern: '일시:\\s*([\\d\\-\\s:]+)',
            amount_pattern: '(?:합계|금액|결제금액|받을금액):\\s*([\\d,]+)'
          };
        }
      } catch (err) {
        console.error('템플릿 정보를 가져오지 못했습니다:', err);
      }
    },
    // 실행 이력 히스토리 조회
    async fetchHistory() {
      this.loadingHistory = true;
      try {
        const response = await getTemplateHistory(this.templateId);
        this.history = response.history || [];
        
        // verify용 패턴 데이터가 history 응답 또는 백엔드 응답을 타면서 parsing_rules를 담고 있으므로 복원
        // 만약 detail 정보가 부족하면 history에서 역조회해 확보
        if (response.parsing_rules) {
          this.parsingRules = response.parsing_rules;
        }
      } catch (err) {
        console.error('실행 이력을 가져오지 못했습니다:', err);
      } finally {
        this.loadingHistory = false;
      }
    },
    // 자가치유 초기화 처리
    async handleResetHealing() {
      if (!confirm('자가 치유 카운터를 초기화하고 블랙리스트 차단을 해제하시겠습니까?')) return;
      this.actionLoading = true;
      try {
        const response = await resetHealing(this.templateId);
        alert('카운터 초기화가 성공적으로 완료되었습니다.');
        // 상태 갱신
        if (response.template) {
          this.template.is_blacklisted = response.template.is_blacklisted;
          this.template.is_verified = response.template.is_verified;
          this.template.self_healing_attempts = response.template.self_healing_attempts;
        }
        await this.fetchTemplateDetails();
        await this.fetchHistory();
      } catch (err) {
        alert(err.message || '초기화 처리에 실패했습니다.');
      } finally {
        this.actionLoading = false;
      }
    },
    // 수동 승격 및 정규식 조율 모달 오픈
    openVerifyModal() {
      this.editRules.date_pattern = this.parsingRules.date_pattern || '';
      this.editRules.amount_pattern = this.parsingRules.amount_pattern || '';
      this.showVerifyModal = true;
    },
    closeVerifyModal() {
      this.showVerifyModal = false;
    },
    // 수동 검증 및 승격 전송
    async handleVerify() {
      if (!this.editRules.date_pattern.trim() || !this.editRules.amount_pattern.trim()) {
        alert('모든 정규식 패턴을 올바르게 채워야 합니다.');
        return;
      }
      this.actionLoading = true;
      try {
        const response = await verifyTemplate(this.templateId, {
          date_pattern: this.editRules.date_pattern,
          amount_pattern: this.editRules.amount_pattern
        });
        alert('템플릿이 성공적으로 수동 승인되어 bypass 파이프라인에 적용되었습니다.');
        
        // 갱신 반영
        if (response.template) {
          this.template.is_verified = response.template.is_verified;
          this.template.is_blacklisted = response.template.is_blacklisted;
          this.template.self_healing_attempts = response.template.self_healing_attempts;
        }
        this.parsingRules.date_pattern = this.editRules.date_pattern;
        this.parsingRules.amount_pattern = this.editRules.amount_pattern;
        
        this.closeVerifyModal();
        await this.fetchTemplateDetails();
        await this.fetchHistory();
      } catch (err) {
        alert(err.message || '승격 처리에 실패했습니다.');
      } finally {
        this.actionLoading = false;
      }
    },
    formatBizNum(val) {
      if (!val) return '-';
      if (val === '0000000000') return '미지정';
      return val.replace(/(\d{3})(\d{2})(\d{5})/, '$1-$2-$3');
    },
    formatDateTime(dateStr) {
      if (!dateStr) return '-';
      try {
        const dt = new Date(dateStr);
        return dt.toLocaleString('ko-KR');
      } catch (e) {
        return dateStr;
      }
    },
    formatDiffValue(field, val) {
      if (val === null || val === undefined) return '-';
      if (field === 'total_amount') {
        return `${Number(val).toLocaleString()}원`;
      }
      if (field === 'transaction_date') {
        return this.formatDateTime(val);
      }
      return val;
    }
  }
};
</script>
