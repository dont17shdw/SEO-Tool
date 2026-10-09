"use client";

import { useState } from "react";
import { OpportunitiesList } from "@/components/opportunities-list";
import { PrioritizedOpportunities } from "@/components/prioritized-opportunities";

/**
 * Keep attention tiers and the original neutral signal listing visibly distinct.
 * 明确区分关注等级与原始中性信号列表。
 */
export function OpportunitiesWorkspace() {
  const [view, setView] = useState<"prioritized" | "neutral">("prioritized");
  return <>
    <div className="toolbar opportunity-view-controls" role="group" aria-label="SEO 机会视图">
      <button type="button" aria-pressed={view === "prioritized"} onClick={() => setView("prioritized")}>优先级视图</button>
      <button type="button" aria-pressed={view === "neutral"} onClick={() => setView("neutral")}>原始事实信号</button>
    </div>
    {view === "prioritized" ? <PrioritizedOpportunities /> : <OpportunitiesList />}
  </>;
}
