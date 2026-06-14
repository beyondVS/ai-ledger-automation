import { getAuthHeader } from './authService';

/**
 * 어드민 가맹점 템플릿 목록을 조회합니다.
 * @param {Object} filters - 필터 옵션 (is_verified, is_blacklisted, vendor_registration_number)
 * @returns {Promise<Object>}
 */
export async function getTemplates(filters = {}) {
  const params = new URLSearchParams();
  if (filters.is_verified !== undefined && filters.is_verified !== '') {
    params.append('is_verified', filters.is_verified);
  }
  if (filters.is_blacklisted !== undefined && filters.is_blacklisted !== '') {
    params.append('is_blacklisted', filters.is_blacklisted);
  }
  if (filters.vendor_registration_number) {
    params.append('vendor_registration_number', filters.vendor_registration_number);
  }

  const response = await fetch(`/api/admin/templates/?${params.toString()}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeader()
    }
  });

  if (!response.ok) {
    throw new Error('템플릿 목록을 불러오는 중 에러가 발생했습니다.');
  }
  return response.json();
}

/**
 * 특정 템플릿의 실행 및 자가 치유 이력을 조회합니다.
 * @param {string} templateId 
 * @returns {Promise<Object>}
 */
export async function getTemplateHistory(templateId) {
  const response = await fetch(`/api/admin/templates/${templateId}/history/`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeader()
    }
  });

  if (!response.ok) {
    throw new Error('템플릿 실행 이력을 불러오는 중 에러가 발생했습니다.');
  }
  return response.json();
}

/**
 * 블랙리스트 템플릿을 수동으로 승격 및 검증 처리합니다.
 * @param {string} templateId 
 * @param {Object} regexPattern 
 * @returns {Promise<Object>}
 */
export async function verifyTemplate(templateId, regexPattern = null, isVerified = null) {
  const payload = {};
  if (regexPattern !== null) {
    payload.regex_pattern = regexPattern;
  }
  if (isVerified !== null) {
    payload.is_verified = isVerified;
  }

  const response = await fetch(`/api/admin/templates/${templateId}/verify/`, {
    method: 'POST',
    body: JSON.stringify(payload),
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeader()
    }
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.message || '템플릿 수동 검증 중 에러가 발생했습니다.');
  }
  return response.json();
}

/**
 * 자가 치유 카운터를 초기화하여 블랙리스트를 수동 해제합니다.
 * @param {string} templateId 
 * @returns {Promise<Object>}
 */
export async function resetHealing(templateId) {
  const response = await fetch(`/api/admin/templates/${templateId}/reset-healing/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeader()
    }
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.message || '자가치유 초기화 처리 중 에러가 발생했습니다.');
  }
  return response.json();
}
