"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { EmptyState } from "@/components/shell/empty-state";
import { buttonVariants } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import { formatPct } from "@/lib/format";
import {
  applyQuizRate,
  gradeQuiz,
  loadQuiz,
  type QuizGrade,
  type QuizQuestion,
} from "@/lib/phase6";

export function AcademyQuiz() {
  const params = useSearchParams();
  const dataset = params.get("dataset") || "dev";
  const [questions, setQuestions] = useState<QuizQuestion[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [index, setIndex] = useState(0);
  const [chosen, setChosen] = useState<Record<string, string>>({});
  const [feedback, setFeedback] = useState<QuizGrade | null>(null);
  const [finalGrade, setFinalGrade] = useState<QuizGrade | null>(null);
  const [applied, setApplied] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setQuestions(null);
    setError(null);
    setIndex(0);
    setChosen({});
    setFeedback(null);
    setFinalGrade(null);
    setApplied(null);
    void loadQuiz(dataset)
      .then((body) => {
        if (!cancelled) setQuestions(body);
      })
      .catch((reason: unknown) => {
        if (!cancelled) setError(reason instanceof ApiError ? reason.message : "The quiz could not be built.");
      });
    return () => {
      cancelled = true;
    };
  }, [dataset]);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (!questions || finalGrade) return;
      const option = questions[index]?.options[Number(event.key) - 1];
      if (option) void pick(option.id);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  async function pick(optionId: string) {
    if (!questions) return;
    const question = questions[index];
    if (!question || chosen[question.id]) return;
    const next = { ...chosen, [question.id]: optionId };
    setChosen(next);
    const answers = Object.entries(next).map(([question_id, choice]) => ({ question_id, chosen: choice }));
    const graded = await gradeQuiz(dataset, answers, false);
    setFeedback(graded);
  }

  async function finish() {
    if (!questions) return;
    const answers = questions.map((question) => ({ question_id: question.id, chosen: chosen[question.id] ?? "" }));
    setFinalGrade(await gradeQuiz(dataset, answers, true));
  }

  if (dataset === "empty") {
    return (
      <EmptyState title="No questions yet">
        Questions are written from real messages. Upload a set in Triage, or open the development corpus.
      </EmptyState>
    );
  }
  if (error) return <EmptyState title="The quiz could not be built">{error}</EmptyState>;
  if (!questions) return <p className="text-sm text-muted-foreground">Building questions from analyzed emails.</p>;
  if (questions.length === 0) {
    return <EmptyState title="No questions yet">This dataset does not have enough analyzed mail to write a quiz.</EmptyState>;
  }
  if (finalGrade) {
    return (
      <section className="max-w-xl border border-border bg-card p-5">
        <h2 className="text-base font-semibold">Score</h2>
        <p className="mt-3 font-mono text-4xl">{formatPct(finalGrade.accuracy)}</p>
        <p className="mt-2 text-sm text-muted-foreground">
          {finalGrade.correct} of {finalGrade.total} correct. Modeled user-layer catch rate {formatPct(finalGrade.catch_rate)}.
        </p>
        {finalGrade.weak_areas.length > 0 ? (
          <p className="mt-3 text-sm">Weak areas: {finalGrade.weak_areas.join(", ")}.</p>
        ) : (
          <p className="mt-3 text-sm">No weak area below 70%.</p>
        )}
        <div className="mt-5 flex flex-wrap gap-2">
          <button
            type="button"
            className={buttonVariants()}
            onClick={() => {
              void applyQuizRate(dataset).then(() => setApplied("User layer set from this quiz. The command center will use it."));
            }}
          >
            Use this accuracy as the user-layer catch rate
          </button>
          <Link href="/" className={buttonVariants({ variant: "outline" })}>Open Command Center</Link>
        </div>
        {applied ? <p className="mt-3 text-sm text-protected">{applied}</p> : null}
      </section>
    );
  }

  const question = questions[index];
  if (!question) return null;
  const result = feedback?.results.find((item) => item.question_id === question.id);
  return (
    <section className="max-w-2xl">
      <p className="text-sm text-muted-foreground">Question {index + 1} of {questions.length}. Keys 1 to 4 choose an answer.</p>
      <article className="mt-4 border border-border bg-card p-5">
        <p className="font-medium">{question.subject || "(no subject)"}</p>
        <p className="mt-1 font-mono text-sm text-muted-foreground">{question.sender}</p>
        {question.excerpt ? (
          <pre className="mt-4 max-h-40 overflow-auto font-mono text-sm leading-6 whitespace-pre-wrap">{question.excerpt}</pre>
        ) : null}
      </article>
      <h2 className="mt-5 text-base font-semibold">{question.prompt}</h2>
      <ol className="mt-3 grid gap-2">
        {question.options.map((option, optionIndex) => {
          const selected = chosen[question.id] === option.id;
          const show = Boolean(result);
          const correct = result?.correct_option_id === option.id;
          const tone = !show ? "" : correct ? "border-protected" : selected ? "border-threat" : "";
          return (
            <li key={option.id}>
              <button
                type="button"
                disabled={Boolean(chosen[question.id])}
                onClick={() => void pick(option.id)}
                className={`w-full border border-border bg-card px-4 py-3 text-left text-sm ${tone}`}
              >
                <span className="mr-3 font-mono text-muted-foreground">{optionIndex + 1}</span>
                {option.text}
              </button>
            </li>
          );
        })}
      </ol>
      {result ? <p className="mt-4 text-sm leading-6">{result.explanation}</p> : null}
      {result ? (
        <button
          type="button"
          className={`${buttonVariants()} mt-4`}
          onClick={() => {
            if (index + 1 >= questions.length) void finish();
            else setIndex(index + 1);
          }}
        >
          {index + 1 >= questions.length ? "See score" : "Next question"}
        </button>
      ) : null}
    </section>
  );
}
