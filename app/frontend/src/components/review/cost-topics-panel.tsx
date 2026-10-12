"use client";

export type CostTopicView = {
  id?: string;
  title?: string;
  status?: string;
  note?: string;
  evidence?: string;
  rate_note?: string;
};

export type CostTopicsView = {
  topics?: CostTopicView[];
};

export function CostTopicsPanel({
  report,
}: Readonly<{ report: CostTopicsView | null | undefined }>) {
  const topics = report?.topics ?? [];
  if (!topics.length) return null;
  return (
    <section className="my-3 rounded-lg border border-navy/20 bg-slate-50 p-3" data-testid="cost-topics-panel">
      <h4 className="text-sm font-bold text-navy">หัวข้อวิเคราะห์งบ ต้นทุน บุคลากร และค่าอบรม</h4>
      <ul className="mt-2 space-y-2">
        {topics.map((topic) => (
          <li key={topic.id || topic.title} className="text-sm text-navy">
            <span className="font-semibold">{topic.title}</span>
            {topic.status ? <span className="ml-2 text-xs">{topic.status}</span> : null}
            {topic.note ? <p className="mt-0.5">{topic.note}</p> : null}
            {topic.evidence ? <p className="mt-0.5 text-xs text-muted-foreground">{topic.evidence}</p> : null}
          </li>
        ))}
      </ul>
    </section>
  );
}
