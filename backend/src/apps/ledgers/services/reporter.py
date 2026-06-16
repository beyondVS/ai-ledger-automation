import sys

from apps.ledgers.models import ReceiptTask
from django.db.models import Count, Max, Min


class ReceiptLoadTestReporter:
    @staticmethod
    def generate_report(user_id=None, task_ids=None):
        """
        ReceiptTask 테이블의 메트릭을 집계하여 리포트를 생성하고 문자열로 반환하며 stdout에 출력합니다.
        """
        queryset = ReceiptTask.objects.all()
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if task_ids:
            queryset = queryset.filter(id__in=task_ids)

        total_count = queryset.count()
        if total_count == 0:
            report_text = "집계할 ReceiptTask 데이터가 없습니다."
            print(report_text)
            return {"total_count": 0, "report_text": report_text}

        # 시간 집계
        time_metrics = queryset.aggregate(min_created=Min("created_at"), max_updated=Max("updated_at"))
        min_created = time_metrics["min_created"]
        max_updated = time_metrics["max_updated"]

        total_duration = 0.0
        if min_created and max_updated:
            total_duration = (max_updated - min_created).total_seconds()

        # 상태별 집계
        status_counts = queryset.values("status").annotate(count=Count("id"))
        status_map = {status: 0 for status, _ in ReceiptTask._meta.get_field("status").choices}
        for item in status_counts:
            status_map[item["status"]] = item["count"]

        # 파서 단계별 집계 (COMPLETED 상태인 것들의 파서 단계 집계)
        stage_counts = queryset.filter(status="COMPLETED").values("parser_stage").annotate(count=Count("id"))
        stage_map = {stage: 0 for stage, _ in ReceiptTask._meta.get_field("parser_stage").choices}
        for item in stage_counts:
            stage_map[item["parser_stage"]] = item["count"]

        # 실패 원인 집계
        failed_reasons = []
        for item in (
            queryset.filter(status="FAILED")
            .exclude(error_message__isnull=True)
            .values("error_message")
            .annotate(count=Count("id"))
        ):
            failed_reasons.append(f"- {item['error_message']}: {item['count']}건")

        completed_count = status_map.get("COMPLETED", 0)
        failed_count = status_map.get("FAILED", 0)
        pending_count = status_map.get("PENDING", 0)
        processing_count = status_map.get("PROCESSING", 0)

        # 텍스트 리포트 조립
        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("        [Receipt Async Load Test Summary Report]")
        report_lines.append("=" * 60)
        report_lines.append(f"총 요청 건수       : {total_count} 건")
        report_lines.append(f"성공 건수          : {completed_count} 건")
        report_lines.append(f"실패 건수          : {failed_count} 건")
        report_lines.append(
            f"진행 중/대기 건수  : {pending_count + processing_count} 건 (Pending: {pending_count}, Processing: {processing_count})"
        )
        report_lines.append(f"총 소요 시간       : {total_duration:.2f} 초")
        if total_duration > 0 and total_count > 0:
            report_lines.append(f"평균 처리 속도     : {total_count / total_duration:.2f} 건/초")
        else:
            report_lines.append("평균 처리 속도     : N/A")

        report_lines.append("-" * 60)
        report_lines.append(" [3-Tier Hybrid Pipeline Stage Statistics (Success Only)]")
        report_lines.append("-" * 60)

        for stage, label in ReceiptTask._meta.get_field("parser_stage").choices:
            if stage == "NONE":
                continue
            count = stage_map.get(stage, 0)
            percentage = (count / completed_count * 100) if completed_count > 0 else 0.0
            report_lines.append(f"- {label:<15} : {count:>2} 건 ({percentage:>6.2f}%)")

        if failed_count > 0:
            report_lines.append("-" * 60)
            report_lines.append(" [Failure Reasons]")
            report_lines.append("-" * 60)
            report_lines.extend(failed_reasons)

        report_lines.append("=" * 60)
        report_text = "\n".join(report_lines)

        print(report_text)
        sys.stdout.flush()

        return {
            "total_count": total_count,
            "completed_count": completed_count,
            "failed_count": failed_count,
            "total_duration": total_duration,
            "stage_stats": stage_map,
            "report_text": report_text,
        }
