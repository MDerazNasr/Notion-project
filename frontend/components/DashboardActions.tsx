"use client";

import { useRouter } from "next/navigation";
import { LoaderCircle, LogOut, RefreshCw } from "lucide-react";
import { useState } from "react";

type DashboardActionsProps = {
  source: string;
};

export function DashboardActions({ source }: DashboardActionsProps) {
  const router = useRouter();
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isSigningOut, setIsSigningOut] = useState(false);

  if (source !== "live") {
    return null;
  }

  async function refreshLiveScores() {
    setIsRefreshing(true);

    try {
      await fetch("/api/score/live", {
        method: "POST"
      });
      router.refresh();
    } finally {
      setIsRefreshing(false);
    }
  }

  async function logout() {
    setIsSigningOut(true);

    try {
      await fetch("/api/notion/logout", {
        method: "POST"
      });
      router.push("/");
      router.refresh();
    } finally {
      setIsSigningOut(false);
    }
  }

  return (
    <div className="flex flex-wrap gap-3">
      <button
        type="button"
        className="button button-secondary"
        onClick={refreshLiveScores}
        disabled={isRefreshing || isSigningOut}
      >
        {isRefreshing ? (
          <LoaderCircle size={16} className="animate-spin" />
        ) : (
          <RefreshCw size={16} />
        )}
        Refresh live score
      </button>
      <button
        type="button"
        className="button button-secondary"
        onClick={logout}
        disabled={isRefreshing || isSigningOut}
      >
        {isSigningOut ? (
          <LoaderCircle size={16} className="animate-spin" />
        ) : (
          <LogOut size={16} />
        )}
        Disconnect
      </button>
    </div>
  );
}
