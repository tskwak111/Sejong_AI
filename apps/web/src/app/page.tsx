import HomeScreen from "./home-screen";

/**
 * 시민 첫 화면 - server-only 모드 결정 (태성 리뷰 2).
 * CHAT_UI_MODE 미설정 시 actual이 기본이고, fixture는 명시 설정에서만
 * 활성화된다. fixture일 때 첫 화면에도 시연용 샘플 배너를 켠다.
 */
export const dynamic = "force-dynamic";

export default function HomePage() {
  return <HomeScreen fixtureMode={process.env.CHAT_UI_MODE === "fixture"} />;
}
