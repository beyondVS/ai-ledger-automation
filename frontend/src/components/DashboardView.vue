<template>
  <main class="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex flex-col items-center justify-center p-6 sm:p-12 selection:bg-indigo-500 transition-colors duration-300">
    <!-- 공통 네비바 컴포넌트 장착 -->
    <NavBar />

    <div class="w-full max-w-lg md:max-w-4xl lg:max-w-5xl flex flex-col mb-16 md:mb-0">
      <!-- 헤더 브랜드 영역 (Aesthetics WOW - Outfit/Inter 모던 타이틀) -->
        <header class="text-center md:text-left select-none max-w-xl mb-8 md:mb-10">
          <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20 mb-3 tracking-wide uppercase font-outfit">
            AI Automations
          </span>
          <h1 class="font-outfit text-4xl md:text-5xl font-black text-slate-900 dark:text-slate-100 tracking-tight leading-none mb-3">
            Smart Ledger <span class="bg-clip-text text-transparent bg-gradient-to-r from-emerald-500 via-teal-500 to-indigo-500 dark:from-emerald-400 dark:via-teal-400 dark:to-indigo-400">Receipts</span>
          </h1>
          <p class="text-slate-600 dark:text-slate-400 text-sm leading-relaxed break-keep">
            영수증 이미지를 올리면 고속 캐시 및 AI가 분석하여 가계부를 자동 작성합니다.
          </p>
        </header>

      <!-- 에러 피드백 알럿 영역 -->
      <div 
        v-if="errorMessage"
        class="w-full max-w-md md:max-w-none mx-auto mb-5 p-4 rounded-xl bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900/40 text-rose-800 dark:text-rose-200 text-sm flex items-start space-x-3 transition-all duration-300 shadow-md animate-fade-in"
      >
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5 flex-shrink-0 mt-0.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <span>{{ errorMessage }}</span>
      </div>

      <!-- 다차원 검색 필터 패널 -->
      <FilterPanel @filter-change="onFilterChange" />

      <!-- 모바일 전용 탭 바 (md 미만 노출) -->
      <div class="flex md:hidden w-full max-w-md mx-auto mb-6 bg-slate-200/60 dark:bg-slate-900 p-1 rounded-xl border border-slate-300 dark:border-slate-800/80">
        <button 
          @click="currentTab = 'upload'" 
          class="flex-1 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer" 
          :class="currentTab === 'upload' ? 'bg-white dark:bg-slate-800 text-indigo-600 dark:text-indigo-400 shadow-sm' : 'text-slate-500 dark:text-slate-400'"
        >
          업로드 & 가맹점
        </button>
        <button 
          @click="currentTab = 'stats'" 
          class="flex-1 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer" 
          :class="currentTab === 'stats' ? 'bg-white dark:bg-slate-800 text-indigo-600 dark:text-indigo-400 shadow-sm' : 'text-slate-500 dark:text-slate-400'"
        >
          내역 & 예산 통계
        </button>
      </div>

      <!-- 상단 대시보드 패널 (예산 게이지 및 TOP 3 가맹점) -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8 w-full items-stretch">
        <BudgetGauge 
          :budget="dashboardData.budget" 
          :current-month-str="currentMonthStr"
          @budget-updated="onBudgetUpdated"
          class="md:block"
          :class="currentTab === 'stats' ? 'block' : 'hidden'"
        />
        <TopMerchants 
          :merchants="dashboardData.top_merchants" 
          class="md:block"
          :class="currentTab === 'upload' ? 'block' : 'hidden'"
        />
      </div>

      <!-- 반응형 그리드 / 세로 배치 본문 레이아웃 (캘린더 뷰 동적 1열 확장 대응) -->
      <div :class="viewMode === 'calendar' ? 'flex flex-col gap-8 w-full mt-2' : 'grid grid-cols-1 md:grid-cols-2 gap-8 items-stretch w-full mt-2'">
        <!-- 좌측 열: 메인 인터랙티브 작업 공간 (접이식 아코디언 카드화) -->
        <div 
          class="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-xl transition-all duration-300 mx-auto md:mx-0 md:block relative"
          :class="[
            viewMode === 'calendar' ? 'w-full order-2' : 'max-w-md md:max-w-none',
            currentTab === 'upload' ? 'block' : 'hidden'
          ]"
        >
          <!-- 카드 헤더 및 접기 토글 -->
          <div class="flex justify-between items-center pb-3 border-b border-slate-100 dark:border-slate-800 mb-4 cursor-pointer select-none" @click="isUploadExpanded = !isUploadExpanded">
            <div class="flex items-center gap-2">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.2" stroke="currentColor" class="w-4 h-4 text-indigo-500">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v6m3-3H9m12 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
              </svg>
              <span class="text-xs font-black text-slate-700 dark:text-slate-200 tracking-tight">새로운 영수증 등록 및 AI 분석</span>
            </div>
            <button class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors">
              <svg v-if="isUploadExpanded" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-4 h-4">
                <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 15.75 7.5-7.5 7.5 7.5" />
              </svg>
              <svg v-else xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-4 h-4">
                <path stroke-linecap="round" stroke-linejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
              </svg>
            </button>
          </div>

          <!-- 아코디언 콘텐츠 -->
          <transition name="expand">
            <div v-show="isUploadExpanded" class="relative">
              <!-- 업로드 진행 중 로딩 인디케이터 오버레이 -->
              <div 
                v-if="isUploading"
                class="absolute inset-0 z-50 bg-white/85 dark:bg-slate-950/80 backdrop-blur-sm rounded-2xl flex flex-col items-center justify-center text-center p-8 border border-slate-200 dark:border-slate-800 shadow-2xl animate-fade-in"
              >
                <!-- 핀테크 감성 그라데이션 회전 링 -->
                <div class="w-14 h-14 rounded-full border-4 border-slate-200 dark:border-slate-800 border-t-indigo-500 dark:border-t-indigo-400 animate-spin mb-4"></div>
                <h3 class="font-outfit text-slate-900 dark:text-slate-100 font-semibold text-lg mb-1">영수증 분석 중...</h3>
                <p class="text-slate-500 dark:text-slate-400 text-xs tracking-wide">HTML5 Canvas 압축 및 AI OCR 파이프라인 가동 중</p>
              </div>

              <!-- 드롭존 -->
              <Dropzone 
                v-if="!currentFile"
                @file-detected="onFileDetected"
                @validation-error="onValidationError"
              />

              <!-- 영수증 결과물 목록 및 분석된 가계부 명세 피드백 -->
              <ReceiptList 
                v-else
                :file="currentFile"
                :parsed-data="parsedData"
                :polling-status="pollingStatus"
                @file-removed="onFileRemoved"
              />
            </div>
          </transition>
        </div>

        <!-- 우측 열: 가계부 리스트/캘린더 뷰 영역 (US1 MVP) -->
        <section 
          class="w-full p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xl flex flex-col justify-between h-full transition-all duration-300 md:block"
          :class="[
            viewMode === 'calendar' ? 'w-full order-1' : 'max-w-md md:max-w-none',
            currentTab === 'stats' ? 'block' : 'hidden'
          ]"
        >
          <div class="flex justify-between items-center mb-6">
            <div class="flex items-center gap-2 select-none">
              <button 
                @click="changeMonth(-1)"
                class="p-1.5 rounded-lg bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-850 transition-all cursor-pointer"
              >
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-4 h-4">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
                </svg>
              </button>
              <span class="text-xs font-semibold text-slate-700 dark:text-slate-300 tracking-wider font-mono uppercase">
                {{ selectedYear }}년 {{ selectedMonth }}월 지출
              </span>
              <button 
                @click="changeMonth(1)"
                class="p-1.5 rounded-lg bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-850 transition-all cursor-pointer"
              >
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-4 h-4">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                </svg>
              </button>
            </div>

            <!-- 목록 / 달력 토글 버튼 스위치 -->
            <div class="flex items-center gap-2.5">
              <div class="flex bg-slate-100 dark:bg-slate-950 p-0.5 rounded-lg border border-slate-200 dark:border-slate-800 text-3xs sm:text-2xs font-bold select-none">
                <button 
                  @click="viewMode = 'list'"
                  class="px-2 py-1 rounded-md transition-all cursor-pointer"
                  :class="viewMode === 'list' ? 'bg-white dark:bg-slate-800 text-indigo-600 dark:text-indigo-400 shadow-sm' : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'"
                >
                  목록
                </button>
                <button 
                  @click="viewMode = 'calendar'"
                  class="px-2 py-1 rounded-md transition-all cursor-pointer"
                  :class="viewMode === 'calendar' ? 'bg-white dark:bg-slate-800 text-indigo-600 dark:text-indigo-400 shadow-sm' : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'"
                >
                  달력
                </button>
              </div>
              <span class="text-indigo-600 dark:text-indigo-400 font-bold font-outfit text-sm hidden sm:inline-block">
                {{ viewMode === 'list' ? formattedMonthlyTotal : calendarMonthlyTotal.toLocaleString() }} 원
              </span>
            </div>
          </div>

          <!-- 1. 목록 뷰 모드 -->
          <div v-if="viewMode === 'list'">
            <!-- 빈 화면 대응 -->
            <div v-if="ledgerList.length === 0 && pendingJobs.length === 0" class="text-center py-8 text-slate-400 dark:text-slate-500 text-xs">
              선택하신 달의 가계부 지출 내역이 없습니다.
            </div>

            <!-- 가계부 카드 목록 (데스크톱 반응형 가변 높이 적용) -->
            <div v-else class="space-y-3 max-h-96 md:max-h-[500px] lg:max-h-[640px] overflow-y-auto pr-1">
              <!-- 비동기 분석 대기중인 스켈레톤 로더 -->
              <LedgerShimmer
                v-for="job in pendingJobs"
                :key="job.id"
                :job="job"
                class="mb-3 animate-fade-in"
              />

              <LedgerListItem 
                v-for="ledger in ledgerList" 
                :key="ledger.id"
                :ledger="ledger"
                @edit="openEditModal"
                @delete="openDeleteModal"
              />
            </div>
          </div>

          <!-- 2. 캘린더 뷰 모드 -->
          <div v-else-if="viewMode === 'calendar'" class="animate-fade-in">
            <CalendarView 
              :year="selectedYear" 
              :month="selectedMonth" 
              :daily-summaries="calendarSummaries"
              @date-click="onCalendarDateClick"
            />
          </div>
        </section>
      </div>

      <!-- 하단 소비 시각화 차트 영역 -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-8 mt-8 w-full items-stretch">
        <!-- 원형 차트 -->
        <div 
          class="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-xl transition-all duration-300 hover:border-slate-350 dark:hover:border-slate-700 flex flex-col justify-between md:block"
          :class="currentTab === 'stats' ? 'block' : 'hidden'"
        >
          <h3 class="text-sm font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-6">카테고리별 지출 비율</h3>
          <div v-if="dashboardData.category_spending && dashboardData.category_spending.length > 0" class="flex items-center justify-center h-[260px]">
            <PieChart :chart-data="pieChartData" :key="`${pieChartData.datasets[0].data.join(',')}-${isDarkMode}`" />
          </div>
          <div v-else class="flex flex-col items-center justify-center h-[260px] text-slate-400 dark:text-slate-500 text-sm border border-dashed border-slate-200 dark:border-slate-800 rounded-xl">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-10 h-10 mb-3 text-slate-400 dark:text-slate-600">
              <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 6a7.5 7.5 0 1 0 7.5 7.5h-7.5V6Z" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 10.5H21A7.5 7.5 0 0 0 13.5 3v7.5Z" />
            </svg>
            <span>이번 달 카테고리별 지출 내역이 없습니다.</span>
          </div>
        </div>

        <!-- 막대 차트 -->
        <div 
          class="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-xl transition-all duration-300 hover:border-slate-350 dark:hover:border-slate-700 flex flex-col justify-between md:block"
          :class="currentTab === 'stats' ? 'block' : 'hidden'"
        >
          <div class="flex justify-between items-center mb-6">
            <h3 class="text-sm font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              월별 지출 추이
              <span class="text-slate-400 dark:text-slate-500 text-3xs font-medium lowercase ml-1.5">(단위: 만원)</span>
            </h3>
            
            <!-- 기간 필터 버튼 그룹 -->
            <div class="flex bg-slate-100 dark:bg-slate-950 p-1 rounded-lg border border-slate-200 dark:border-slate-800 text-xs">
              <button 
                v-for="m in [3, 6, 12]" 
                :key="m"
                @click="updateMonthsFilter(m)"
                class="px-3 py-1 rounded-md font-medium transition-all cursor-pointer"
                :class="selectedMonthsFilter === m ? 'bg-indigo-600 dark:bg-indigo-500 text-white shadow-sm' : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'"
              >
                {{ m }}개월
              </button>
            </div>
          </div>
          <div v-if="dashboardData.monthly_trends && dashboardData.monthly_trends.length > 0" class="h-[260px] flex items-center justify-center">
            <BarChart :chart-data="barChartData" :key="`${barChartData.datasets[0].data.join(',')}-${isDarkMode}`" />
          </div>
          <div v-else class="flex flex-col items-center justify-center h-[260px] text-slate-400 dark:text-slate-500 text-sm border border-dashed border-slate-200 dark:border-slate-800 rounded-xl">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-10 h-10 mb-3 text-slate-400 dark:text-slate-600">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v5.25c0 .621-.504 1.125-1.125 1.125h-2.25A1.125 1.125 0 0 1 3 18.375v-5.25ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125v-9.75ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v14.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" />
            </svg>
            <span>지출 통계 분석 데이터가 없습니다.</span>
          </div>
        </div>
      </div>

      <!-- 모바일 전용 Bottom Navigation Bar (md 미만 하단 고정) -->
      <nav class="fixed bottom-0 left-0 right-0 z-40 bg-white/95 dark:bg-slate-950/95 border-t border-slate-200 dark:border-slate-800 backdrop-blur-md px-6 py-2 flex justify-around md:hidden shadow-lg">
        <button 
          @click="currentTab = 'upload'"
          class="flex flex-col items-center gap-0.5 text-slate-500 dark:text-slate-400 cursor-pointer"
          :class="{ 'text-indigo-600 dark:text-indigo-400 font-bold': currentTab === 'upload' }"
        >
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 16.5V9.75m0 0 3 3m-3-3-3 3M6.75 19.5a4.5 4.5 0 0 1-1.41-8.775 5.25 5.25 0 0 1 10.233-2.33 3 3 0 0 1 3.758 3.848A3.752 3.752 0 0 1 18 19.5H6.75Z" />
          </svg>
          <span class="text-3xs uppercase tracking-wide">업로드</span>
        </button>

        <button 
          @click="currentTab = 'stats'"
          class="flex flex-col items-center gap-0.5 text-slate-500 dark:text-slate-400 cursor-pointer"
          :class="{ 'text-indigo-600 dark:text-indigo-400 font-bold': currentTab === 'stats' }"
        >
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v5.25c0 .621-.504 1.125-1.125 1.125h-2.25A1.125 1.125 0 0 1 3 18.375v-5.25ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125v-9.75ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v14.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" />
          </svg>
          <span class="text-3xs uppercase tracking-wide">내역/통계</span>
        </button>

        <button 
          @click="goToMyTemplates"
          class="flex flex-col items-center gap-0.5 text-slate-500 dark:text-slate-400 cursor-pointer"
        >
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 6h9.75M10.5 6a1.5 1.5 0 1 1-3 0m3 0a1.5 1.5 0 1 0-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m-9.75 0h9.75" />
          </svg>
          <span class="text-3xs uppercase tracking-wide">템플릿</span>
        </button>

        <button 
          @click="handleLogout"
          class="flex flex-col items-center gap-0.5 text-slate-500 dark:text-slate-400 cursor-pointer"
        >
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0 0 13.5 3h-6a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h6a2.25 2.25 0 0 0 2.25-2.25V15M12 9l-3 3m0 0 3 3m-3-3h12.75" />
          </svg>
          <span class="text-3xs uppercase tracking-wide">로그아웃</span>
        </button>
      </nav>

      <!-- 정보 푸터 -->
      <footer class="text-center text-slate-600 text-xs font-mono tracking-wider mt-12 select-none">
        AI Ledger Automation v1.0.0 &copy; 2026
      </footer>
    </div>

    <!-- 수정 모달 (T013) -->
    <LedgerEditModal
      :is-open="isEditModalOpen"
      :ledger="selectedLedgerForEdit || {}"
      @close="isEditModalOpen = false"
      @save="handleEditSave"
    />

    <!-- 삭제 경고 모달 (T020) -->
    <LedgerDeleteModal
      :is-open="isDeleteModalOpen"
      :ledger="selectedLedgerForDelete || {}"
      @close="isDeleteModalOpen = false"
      @confirm="handleDeleteConfirm"
    />

    <!-- 일자별 상세 조회 모달 팝업 -->
    <transition name="fade">
      <div 
        v-if="isDateDetailModalOpen" 
        class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/40 backdrop-blur-sm"
        @click.self="isDateDetailModalOpen = false"
      >
        <div class="w-full max-w-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-2xl animate-fade-in max-h-[85vh] flex flex-col">
          <!-- 모달 헤더 -->
          <div class="flex justify-between items-center border-b border-slate-100 dark:border-slate-800 pb-3 mb-4 select-none">
            <div>
              <h3 class="text-base font-bold text-slate-900 dark:text-slate-100 font-mono">
                {{ selectedDateForDetail }}
              </h3>
              <p class="text-4xs text-slate-400 mt-0.5">선택하신 날짜에 작성된 상세 지출 명세 목록입니다.</p>
            </div>
            <button 
              @click="isDateDetailModalOpen = false"
              class="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors cursor-pointer"
            >
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <!-- 상세 리스트 -->
          <div class="overflow-y-auto flex-1 space-y-3 pr-1 py-1">
            <div v-if="dateDetailLedgers.length === 0" class="text-center py-6 text-slate-400 dark:text-slate-500 text-xs">
              해당 날짜의 가계부 내역이 존재하지 않습니다.
            </div>
            <div 
              v-for="ledger in dateDetailLedgers" 
              :key="ledger.id"
              class="p-3 bg-slate-50 dark:bg-slate-950 border border-slate-200/50 dark:border-slate-800 rounded-xl flex items-center justify-between gap-3 group transition-all"
            >
              <div class="min-w-0 flex-1">
                <h4 class="text-xs font-bold text-slate-800 dark:text-slate-100 tracking-tight truncate">{{ ledger.vendor_name }}</h4>
                <div class="flex items-center gap-1.5 mt-1 flex-wrap">
                  <span class="text-4xs font-bold px-1.5 py-0.5 rounded bg-slate-200/50 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                    {{ ledger.category }}
                  </span>
                  <span v-if="ledger.transaction_date" class="text-4xs text-slate-400 dark:text-slate-500 font-mono">
                    {{ ledger.transaction_date.substring(11, 16) }}
                  </span>
                </div>
              </div>
              <div class="flex items-center gap-3 flex-shrink-0">
                <span class="text-xs font-black text-slate-900 dark:text-indigo-400">
                  {{ Number(ledger.total_amount).toLocaleString() }}원
                </span>
                <!-- 편집제어 액션 버튼들 -->
                <div class="flex gap-1">
                  <button 
                    @click="openEditModal(ledger)"
                    class="p-1 rounded bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-500 hover:text-indigo-500 dark:hover:text-indigo-400 hover:border-indigo-200 transition-all cursor-pointer"
                    title="수정"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-3.5 h-3.5">
                      <path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10" />
                    </svg>
                  </button>
                  <button 
                    @click="openDeleteModal(ledger)"
                    class="p-1 rounded bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-950/20 transition-all cursor-pointer"
                    title="삭제"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-3.5 h-3.5">
                      <path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.244 2.244 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- 모달 푸터 -->
          <div class="border-t border-slate-100 dark:border-slate-800 pt-3 mt-4 flex justify-end select-none">
            <button 
              @click="isDateDetailModalOpen = false"
              class="px-4 py-2 rounded-xl bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 hover:bg-slate-200 dark:hover:bg-slate-850 text-slate-700 dark:text-slate-300 font-semibold text-xs transition-all cursor-pointer"
            >
              닫기
            </button>
          </div>
        </div>
      </div>
    </transition>
  </main>
</template>

<script>
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import NavBar from './NavBar.vue';
import Dropzone from './Dropzone.vue';
import ReceiptList from './ReceiptList.vue';
import LedgerListItem from './LedgerListItem.vue';
import LedgerShimmer from './LedgerShimmer.vue';
import PieChart from './PieChart.vue';
import BarChart from './BarChart.vue';
import BudgetGauge from './BudgetGauge.vue';
import TopMerchants from './TopMerchants.vue';
import CalendarView from './CalendarView.vue';
import FilterPanel from './FilterPanel.vue';
import { compressImage, uploadReceiptApi } from '../services/uploadService';
import { fetchLedgerList, fetchLedgerCalendar } from '../services/ledgerService';
import { fetchDashboardStatistics } from '../services/dashboardService';
import { VirtualPollingManager } from '../services/pollingService';
import { fetchUserTimezone } from '../services/accountService';
import { logout } from '../services/authService';
import LedgerEditModal from './LedgerEditModal.vue';
import LedgerDeleteModal from './LedgerDeleteModal.vue';

export default {
  name: 'DashboardView',
  components: {
    NavBar,
    Dropzone,
    ReceiptList,
    LedgerListItem,
    LedgerShimmer,
    LedgerEditModal,
    LedgerDeleteModal,
    PieChart,
    BarChart,
    BudgetGauge,
    TopMerchants,
    CalendarView,
    FilterPanel
  },
  setup() {
    const router = useRouter();
    const currentUsername = ref('사용자');
    const currentFile = ref(null);
    const parsedData = ref(null);
    const isUploading = ref(false);
    const errorMessage = ref(null);
    let errorTimeout = null;
    const ledgerList = ref([]);
    const pendingJobs = ref([]);
    const pollingStatus = ref(null);
    // 캘린더 및 다차원 복합 필터 모드 관련 상태
    const viewMode = ref('list'); // 'list' | 'calendar'
    const isUploadExpanded = ref(true);
    const userTimezone = ref('Asia/Seoul');
    const calendarSummaries = ref({});
    const calendarMonthlyTotal = ref(0);
    const activeFilters = ref({
      q: '',
      categories: '',
      min_amount: '',
      max_amount: ''
    });

    // 캘린더 일자 클릭 시 상세 내역 모달 관련 상태
    const isDateDetailModalOpen = ref(false);
    const selectedDateForDetail = ref('');
    const dateDetailLedgers = computed(() => {
      if (!selectedDateForDetail.value) return [];
      const tz = userTimezone.value && userTimezone.value.trim() ? userTimezone.value : 'Asia/Seoul';
      const filtered = ledgerList.value.filter(item => {
        if (!item.transaction_date) return false;
        try {
          const date = new Date(item.transaction_date);
          const formatter = new Intl.DateTimeFormat('sv-SE', {
            timeZone: tz,
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
          });
          return formatter.format(date) === selectedDateForDetail.value;
        } catch (e) {
          console.error('Failed to convert timezone date for detail filtering', e);
          return item.transaction_date.substring(0, 10) === selectedDateForDetail.value;
        }
      });
      console.log(`[DateClickDetail] Filtered items for date ${selectedDateForDetail.value} (timezone: ${tz}):`, filtered.length, 'items found from total', ledgerList.value.length);
      return filtered;
    });

    // 테마 및 모바일 탭 상태
    const isDarkMode = ref(true);
    const currentTab = ref('upload');

    const toggleTheme = () => {
      isDarkMode.value = !isDarkMode.value;
      document.documentElement.classList.toggle('dark', isDarkMode.value);
      localStorage.setItem('theme', isDarkMode.value ? 'dark' : 'light');
    };

    // 선택된 년/월 상태 변수 (US1 MVP)
    const today = new Date();
    const selectedYear = ref(today.getFullYear());
    const selectedMonth = ref(today.getMonth() + 1);

    // 모달 활성화 상태 및 타겟 정보 refs
    const isEditModalOpen = ref(false);
    const selectedLedgerForEdit = ref(null);
    const isDeleteModalOpen = ref(false);
    const selectedLedgerForDelete = ref(null);

    // 대시보드 통계 상태 정보 (US1, US2, US3)
    const dashboardData = ref({
      budget: { amount: 1000000, spent_amount: 0, remaining_amount: 1000000, spent_ratio: 0, status: 'safe' },
      category_spending: [],
      monthly_trends: [],
      top_merchants: []
    });
    const selectedMonthsFilter = ref(3);

    const currentMonthStr = computed(() => {
      return `${selectedYear.value}-${String(selectedMonth.value).padStart(2, '0')}`;
    });

    const openEditModal = (ledger) => {
      selectedLedgerForEdit.value = ledger;
      isEditModalOpen.value = true;
    };

    const openDeleteModal = (ledger) => {
      selectedLedgerForDelete.value = ledger;
      isDeleteModalOpen.value = true;
    };

    const handleEditSave = (updatedLedger) => {
      ledgerList.value = ledgerList.value.map(item => 
        item.id === updatedLedger.id ? updatedLedger : item
      );
      // 대시보드 실시간 지표 갱신
      loadDashboardData();
    };

    const handleDeleteConfirm = () => {
      if (selectedLedgerForDelete.value) {
        ledgerList.value = ledgerList.value.filter(item => 
          item.id !== selectedLedgerForDelete.value.id
        );
      }
      // 대시보드 실시간 지표 갱신
      loadDashboardData();
    };

    const onBudgetUpdated = (updatedBudget) => {
      // 게이지 수정 즉시 화면을 갱신
      dashboardData.value.budget = {
        amount: Number(updatedBudget.amount),
        spent_amount: dashboardData.value.budget.spent_amount,
        remaining_amount: Number(updatedBudget.amount) - dashboardData.value.budget.spent_amount,
        spent_ratio: (dashboardData.value.budget.spent_amount / Number(updatedBudget.amount)) * 100,
        status: (dashboardData.value.budget.spent_amount / Number(updatedBudget.amount)) * 100 < 50 ? 'safe' : 
                (dashboardData.value.budget.spent_amount / Number(updatedBudget.amount)) * 100 <= 80 ? 'warning' : 'danger'
      };
      // 백엔드 전체 연동 갱신
      loadDashboardData();
    };

    onMounted(() => {
      // 테마 초기 로딩 동기화
      const savedTheme = localStorage.getItem('theme');
      if (savedTheme === 'light') {
        isDarkMode.value = false;
        document.documentElement.classList.remove('dark');
      } else {
        isDarkMode.value = true;
        document.documentElement.classList.add('dark');
      }

      loadUserTimezone();
      loadLedgerList();
      loadDashboardData();
      const sessionData = sessionStorage.getItem('ai_ledger_auth_session');
      if (sessionData) {
        try {
          const parsed = JSON.parse(sessionData);
          if (parsed && parsed.username) {
            currentUsername.value = parsed.username;
          }
        } catch (e) {
          console.error('Failed to parse session info', e);
        }
      }
    });

    const loadUserTimezone = async () => {
      try {
        const response = await fetchUserTimezone();
        if (response && response.data && response.data.timezone) {
          userTimezone.value = response.data.timezone;
        }
      } catch (err) {
        console.error('Failed to load user timezone in Dashboard', err);
      }
    };

    const loadLedgerList = async () => {
      try {
        const data = await fetchLedgerList(selectedYear.value, selectedMonth.value, activeFilters.value);
        ledgerList.value = data;
        loadCalendarData();
      } catch (err) {
        console.error('Failed to load ledger list', err);
      }
    };

    const onFilterChange = (newFilters) => {
      activeFilters.value = newFilters;
      loadLedgerList();
    };

    const loadCalendarData = async () => {
      try {
        const response = await fetchLedgerCalendar(selectedYear.value, selectedMonth.value, activeFilters.value);
        if (response && response.status === 'success') {
          calendarSummaries.value = response.data.daily_summaries;
          calendarMonthlyTotal.value = response.data.monthly_total;
        }
      } catch (err) {
        console.error('Failed to load calendar data', err);
      }
    };

    const onCalendarDateClick = (dateStr) => {
      console.log(`[CalendarDateClick] User clicked date: ${dateStr}`);
      selectedDateForDetail.value = dateStr;
      isDateDetailModalOpen.value = true;
    };

    const loadDashboardData = async () => {
      try {
        const data = await fetchDashboardStatistics(selectedMonthsFilter.value);
        dashboardData.value = data;
      } catch (err) {
        console.error('Failed to load dashboard statistics', err);
      }
    };

    const updateMonthsFilter = (months) => {
      selectedMonthsFilter.value = months;
      loadDashboardData();
    };

    // 월 이동 제어 기능 (US1 MVP)
    const changeMonth = (offset) => {
      let year = selectedYear.value;
      let month = selectedMonth.value + offset;

      if (month > 12) {
        month = 1;
        year += 1;
      } else if (month < 1) {
        month = 12;
        year -= 1;
      }

      selectedYear.value = year;
      selectedMonth.value = month;
      loadLedgerList();
      loadDashboardData();
    };

    // 업로드된 영수증 날짜의 월로 대시보드 포커스 강제 동기화 (US1 MVP)
    const syncDashboardMonthToReceipt = (dateStr) => {
      if (!dateStr) return;
      try {
        const date = new Date(dateStr);
        if (!isNaN(date.getTime())) {
          selectedYear.value = date.getFullYear();
          selectedMonth.value = date.getMonth() + 1;
        }
      } catch (e) {
        console.error('Failed to sync dashboard month to receipt date', e);
      }
    };

    const handleLogout = async () => {
      try {
        await logout();
        if (router) {
          router.push({ name: 'Login' });
        } else {
          window.location.hash = '/login';
        }
      } catch (err) {
        console.error('Logout error', err);
      }
    };

    const goToMyTemplates = () => {
      if (router) {
        router.push({ name: 'MyTemplateList' });
      } else {
        window.location.hash = '/my/templates';
      }
    };

    // 영수증 파일 감지 성공 시 호출 (비동기 업로드 E2E 구동)
    const onFileDetected = async (file) => {
      isUploadExpanded.value = true;
      clearError();
      isUploading.value = true;
      pollingStatus.value = null;

      try {
        const compressed = await compressImage(file);
        const response = await uploadReceiptApi(compressed, file.name);
        const jobId = response.job_id;
        const status = response.status;
        const previewUrl = URL.createObjectURL(compressed);
        
        currentFile.value = {
          id: jobId,
          name: file.name,
          size: compressed.size,
          type: file.type,
          previewUrl: previewUrl,
          rawFile: file,
          createdAt: new Date().toISOString()
        };

        if (status === 'COMPLETED') {
          parsedData.value = response.data;
          pollingStatus.value = 'COMPLETED';
          syncDashboardMonthToReceipt(response.data.transaction_date);
          loadLedgerList();
          loadDashboardData();
        } else {
          pollingStatus.value = status;
          pendingJobs.value.push({
            id: jobId,
            status: status,
            raw_file_name: file.name
          });
          startVirtualPolling(jobId, status);
        }

      } catch (err) {
        onValidationError(err.message);
        currentFile.value = null;
        parsedData.value = null;
      } finally {
        isUploading.value = false;
      }
    };

    // 가상 폴링 모듈 구동 함수
    const startVirtualPolling = (jobId, initialStatus) => {
      VirtualPollingManager.startPolling(
        jobId,
        initialStatus,
        (completedData) => {
          parsedData.value = completedData;
          pollingStatus.value = 'COMPLETED';
          pendingJobs.value = pendingJobs.value.filter(j => j.id !== jobId);
          syncDashboardMonthToReceipt(completedData.transaction_date);
          loadLedgerList();
          loadDashboardData();
        },
        (error) => {
          onValidationError(error.message || '비동기 폴링 상태 조회에 실패했습니다.');
          pollingStatus.value = 'FAILED';
          pendingJobs.value = pendingJobs.value.filter(j => j.id !== jobId);
        },
        (newStatus) => {
          const job = pendingJobs.value.find(j => j.id === jobId);
          if (job) {
            job.status = newStatus;
          }
        }
      );
    };

    // 영수증 파일 제거 시 (메모리 안전 해제)
    const onFileRemoved = () => {
      if (currentFile.value) {
        URL.revokeObjectURL(currentFile.value.previewUrl);
      }
      currentFile.value = null;
      parsedData.value = null;
      pollingStatus.value = null;
      clearError();
    };

    const onValidationError = (error) => {
      errorMessage.value = error;
      
      if (errorTimeout) clearTimeout(errorTimeout);
      errorTimeout = setTimeout(() => {
        errorMessage.value = null;
      }, 4000);
    };

    const clearError = () => {
      errorMessage.value = null;
      if (errorTimeout) clearTimeout(errorTimeout);
    };

    const formattedMonthlyTotal = computed(() => {
      const total = ledgerList.value.reduce((acc, item) => acc + Number(item.total_amount), 0);
      return total.toLocaleString();
    });

    const pieChartData = computed(() => {
      const categories = dashboardData.value.category_spending || [];
      const colors = [
        '#10B981', // emerald-500
        '#3B82F6', // blue-500
        '#EC4899', // pink-500
        '#F59E0B', // amber-500
        '#8B5CF6', // violet-500
        '#EF4444', // red-500
        '#6B7280'  // gray-500 (미분류 fallback)
      ];
      return {
        labels: categories.map(c => c.category_name),
        datasets: [{
          backgroundColor: categories.map((_, i) => colors[i % colors.length]),
          borderWidth: 0,
          data: categories.map(c => c.amount)
        }]
      };
    });

    const barChartData = computed(() => {
      const trends = dashboardData.value.monthly_trends || [];
      return {
        labels: trends.map(t => t.month),
        datasets: [{
          label: '월별 지출액',
          backgroundColor: 'rgba(79, 70, 229, 0.85)',
          hoverBackgroundColor: 'rgba(79, 70, 229, 1)',
          borderRadius: 6,
          borderSkipped: false,
          data: trends.map(t => t.amount)
        }]
      };
    });

    return {
      isDarkMode,
      currentTab,
      toggleTheme,
      ledgerList,
      pendingJobs,
      formattedMonthlyTotal,
      currentUsername,
      currentFile,
      parsedData,
      isUploading,
      errorMessage,
      pollingStatus,
      isEditModalOpen,
      selectedLedgerForEdit,
      isDeleteModalOpen,
      selectedLedgerForDelete,
      selectedYear,
      selectedMonth,
      dashboardData,
      selectedMonthsFilter,
      currentMonthStr,
      pieChartData,
      barChartData,
      openEditModal,
      openDeleteModal,
      handleEditSave,
      handleDeleteConfirm,
      onBudgetUpdated,
      handleLogout,
      goToMyTemplates,
      onFileDetected,
      onFileRemoved,
      onValidationError,
      changeMonth,
      updateMonthsFilter,
      viewMode,
      userTimezone,
      isUploadExpanded,
      calendarSummaries,
      calendarMonthlyTotal,
      activeFilters,
      isDateDetailModalOpen,
      selectedDateForDetail,
      loadCalendarData,
      onCalendarDateClick,
      onFilterChange
    };
  }
};
</script>

<style scoped>
/* 부드러운 페이드인 애니메이션 */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-5px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-fade-in {
  animation: fadeIn 0.3s ease-out forwards;
}
.word-break-keep-all {
  word-break: keep-all;
}
</style>
