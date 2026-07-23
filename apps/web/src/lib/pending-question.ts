/**
 * 첫 화면 → 대화 화면 질문 전달 - 탭 메모리 전용 (태성 리뷰 1).
 * 질문 원문이 URL·브라우저 히스토리·서버 액세스 로그에 남지 않도록
 * `/chat?q=` 쿼리스트링 대신 모듈 스코프 변수로만 전달한다
 * (CLAUDE.md §9 브라우저 스토리지 금지와 같은 취지 - 스토리지도 쓰지 않는다).
 * consume은 1회성이다 - 읽는 즉시 비워 뒤로가기·재마운트 시 재전송을 막는다.
 * 새 탭으로 열면 값이 없으므로 대화 화면은 빈 상태로 시작한다(의도된 동작).
 */
let pendingQuestion: string | null = null;

export function setPendingQuestion(question: string): void {
  pendingQuestion = question;
}

export function consumePendingQuestion(): string | null {
  const value = pendingQuestion;
  pendingQuestion = null;
  return value;
}
