<template>
  <tr class="hover:bg-slate-100 dark:hover:bg-slate-800/45 transition-colors duration-200 border-b border-slate-200 dark:border-slate-800/50">
    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-slate-850 dark:text-slate-200">
      {{ template.vendor_name }}
    </td>
    <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-550 dark:text-slate-400 font-mono">
      {{ formatBizNum(template.vendor_registration_number) }}
    </td>
    <td class="px-6 py-4 whitespace-nowrap">
      <span v-if="template.is_blacklisted" class="px-3 py-1 rounded-full text-xs font-semibold bg-rose-50 dark:bg-rose-500/20 text-rose-600 dark:text-rose-400 border border-rose-200 dark:border-rose-500/30 shadow-sm animate-pulse">
        🚫 블랙리스트
      </span>
      <span v-else-if="template.is_verified" class="px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/30 shadow-sm">
        ✓ 검증 완료
      </span>
      <span v-else class="px-3 py-1 rounded-full text-xs font-semibold bg-amber-50 dark:bg-amber-500/20 text-amber-600 dark:text-amber-400 border border-amber-200 dark:border-amber-500/30 shadow-sm">
        ⏳ 자동 학습 중
      </span>
    </td>
    <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-600 dark:text-slate-300 font-mono">
      <span :class="template.consistency_count >= 2 ? 'text-emerald-600 dark:text-emerald-400 font-bold' : 'text-slate-600 dark:text-slate-300'">
        {{ template.consistency_count }} / 3
      </span>
    </td>
    <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-600 dark:text-slate-300 font-mono">
      <span :class="template.self_healing_attempts >= 2 ? 'text-rose-600 dark:text-rose-400 font-bold' : 'text-slate-600 dark:text-slate-300'">
        {{ template.self_healing_attempts }} / 3
      </span>
    </td>
    <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-550 dark:text-slate-400">
      {{ formatDate(template.last_healing_at) }}
    </td>
    <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
      <router-link
        :to="`/admin/templates/${template.id}`"
        class="inline-flex items-center px-3.5 py-1.5 border border-slate-300 dark:border-slate-600 rounded-lg text-xs font-semibold text-slate-700 dark:text-slate-200 hover:text-slate-900 hover:bg-slate-100 dark:hover:text-white dark:hover:bg-slate-700 dark:hover:border-slate-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-100 dark:focus:ring-offset-slate-900 focus:ring-emerald-550 dark:focus:ring-emerald-500 transition-all duration-200 shadow-sm"
      >
        상세 및 관리
      </router-link>
    </td>
  </tr>
</template>

<script>
export default {
  name: 'TemplateListItem',
  props: {
    template: {
      type: Object,
      required: true
    }
  },
  methods: {
    formatBizNum(val) {
      if (!val) return '-';
      if (val === '0000000000') return '미지정';
      return val.replace(/(\d{3})(\d{2})(\d{5})/, '$1-$2-$3');
    },
    formatDate(dateStr) {
      if (!dateStr) return '-';
      try {
        const dt = new Date(dateStr);
        return dt.toLocaleString('ko-KR', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit'
        });
      } catch (e) {
        return dateStr;
      }
    }
  }
}
</script>
