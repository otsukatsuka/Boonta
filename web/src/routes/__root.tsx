import { createRootRoute, Outlet, useNavigate, useRouterState } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { TopBar } from "../components/TopBar";
import { StatusBar } from "../components/StatusBar";
import { TweaksPanel, useEvThreshold } from "../components/TweaksPanel";
import { useSystemStatus } from "../hooks/useApi";

function RootLayout() {
  const navigate = useNavigate();
  const state = useRouterState();
  const path = state.location.pathname;
  const tab = path.startsWith("/race")
    ? "race"
    : path.startsWith("/backtest")
      ? "back"
      : path.startsWith("/data")
        ? "data"
        : path.startsWith("/model")
          ? "model"
          : "dash";

  const [evThreshold, setEvThreshold] = useEvThreshold();
  const [clock, setClock] = useState(() =>
    new Date().toLocaleTimeString("ja-JP", { hour12: false }),
  );
  useEffect(() => {
    const t = setInterval(
      () => setClock(new Date().toLocaleTimeString("ja-JP", { hour12: false })),
      1000,
    );
    return () => clearInterval(t);
  }, []);

  const { data: status } = useSystemStatus();
  const date = new Date().toISOString().slice(0, 10);

  function handleTab(id: string) {
    if (id === "dash") navigate({ to: "/" });
    else if (id === "back") navigate({ to: "/backtest" });
    else if (id === "race") {
      // Stay on current race or no-op
    } else {
      navigate({ to: `/${id}` as never });
    }
  }

  return (
    <div className="terminal-frame">
      <TopBar tab={tab} onTab={handleTab} clock={clock} status={status} />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0 }}>
        <Outlet />
      </div>
      <StatusBar tab={tab} evThreshold={evThreshold} status={status} date={date} />
      <TweaksPanel evThreshold={evThreshold} setEvThreshold={setEvThreshold} />
    </div>
  );
}

export const Route = createRootRoute({
  component: RootLayout,
});
