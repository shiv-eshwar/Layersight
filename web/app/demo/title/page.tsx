const CLOSING =
  "Traditional phishing tools tell you what is dangerous. LayerSight tells you how vulnerable you are, where your defenses fail, and what to improve next.";

export const metadata = { title: "LayerSight" };

export default function TitleCardPage() {
  return (
    <section data-testid="title-card" className="mx-auto max-w-2xl py-24 text-center">
      <p className="text-2xl leading-9 font-semibold tracking-tight">{CLOSING}</p>
    </section>
  );
}
