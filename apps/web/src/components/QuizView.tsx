"use client";

import { useState } from "react";
import type { QuizQuestion } from "@/lib/videoTypes";

export function QuizView({ videoId, quiz }: { videoId: string; quiz: QuizQuestion[] }) {
  const [answers, setAnswers] = useState<number[][]>(() => quiz.map(() => []));
  const [submitted, setSubmitted] = useState(false);

  function toggleOption(qIndex: number, optIndex: number) {
    if (submitted) return;
    setAnswers((prev) => {
      const next = [...prev];
      const q = quiz[qIndex];
      if (q.type === "single") {
        next[qIndex] = [optIndex];
      } else {
        const current = next[qIndex];
        next[qIndex] = current.includes(optIndex)
          ? current.filter((i) => i !== optIndex)
          : [...current, optIndex];
      }
      return next;
    });
  }

  function onSubmit() {
    setSubmitted(true);
    fetch(`/api/videos/${videoId}/events`, {
      method: "POST",
      body: JSON.stringify({ event_type: "qa_click" }),
    }).catch(() => {});
  }

  const score = submitted
    ? answers.reduce((total, given, i) => {
        const correct = quiz[i].correct_indices;
        const isCorrect =
          given.length === correct.length && given.every((v) => correct.includes(v));
        return total + (isCorrect ? 1 : 0);
      }, 0)
    : 0;

  return (
    <div className="flex flex-col gap-6 max-w-2xl">
      {quiz.map((q, qIndex) => {
        const given = answers[qIndex];
        return (
          <div key={qIndex} className="border border-black/10 dark:border-white/10 rounded-lg p-4">
            <p className="font-medium mb-3">
              {qIndex + 1}. {q.question}{" "}
              <span className="text-xs text-black/50 dark:text-white/50">
                ({q.type === "multi" ? "select all that apply" : "select one"})
              </span>
            </p>
            <div className="flex flex-col gap-2">
              {q.options.map((opt, optIndex) => {
                const isChecked = given.includes(optIndex);
                const isCorrectOption = q.correct_indices.includes(optIndex);
                let extraClass = "border-black/10 dark:border-white/10";
                if (submitted) {
                  if (isCorrectOption) extraClass = "border-green-500";
                  else if (isChecked) extraClass = "border-red-500";
                }
                return (
                  <label
                    key={optIndex}
                    className={`flex items-center gap-2 border rounded px-3 py-2 text-sm cursor-pointer ${extraClass}`}
                  >
                    <input
                      type={q.type === "multi" ? "checkbox" : "radio"}
                      checked={isChecked}
                      onChange={() => toggleOption(qIndex, optIndex)}
                      disabled={submitted}
                    />
                    {opt}
                  </label>
                );
              })}
            </div>
          </div>
        );
      })}

      {submitted ? (
        <p className="text-lg font-semibold">
          Score: {score} out of {quiz.length}
        </p>
      ) : (
        <button
          onClick={onSubmit}
          className="bg-foreground text-background rounded px-4 py-2 text-sm font-medium w-fit"
        >
          Submit
        </button>
      )}
    </div>
  );
}
