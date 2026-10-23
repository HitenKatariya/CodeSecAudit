"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { fetchMe } from "@/lib/api";

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    let isMounted = true;
    fetchMe()
      .then((user) => {
        if (!isMounted) return;
        if (user) {
          router.replace("/dashboard");
        } else {
          router.replace("/login");
        }
      })
      .catch(() => {
        if (!isMounted) return;
        router.replace("/login");
      });

    return () => {
      isMounted = false;
    };
  }, [router]);

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100vh",
        background: "var(--bg-canvas, #090d16)",
      }}
    >
      <div
        style={{
          width: "32px",
          height: "32px",
          border: "3px solid rgba(255,255,255,0.1)",
          borderTopColor: "var(--accent, #3b82f6)",
          borderRadius: "50%",
          animation: "spin 0.8s linear infinite",
        }}
      />
    </div>
  );
}
