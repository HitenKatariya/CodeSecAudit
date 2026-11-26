"use client";

import React, { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { ShieldCheckIcon, AlertTriangleIcon, GitHubIcon } from "@/components/ui/Icons";
import { Button } from "@/components/ui/Button";
import { acceptInvitation, fetchMe } from "@/lib/api";
import { UserProfile } from "@/types";

function AcceptInviteContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";

  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    fetchMe().then((me) => {
      if (!mounted) return;
      setUser(me);
      setLoading(false);
    });
    return () => {
      mounted = false;
    };
  }, []);

  const handleAccept = async () => {
    if (!token) {
      setError("No invitation token found in the URL.");
      return;
    }
    setSubmitting(true);
    setError(null);

    const res = await acceptInvitation(token);
    if (res.ok) {
      setSuccess(true);
      setTimeout(() => {
        router.push("/dashboard");
      }, 2000);
    } else {
      setError(res.message || "Failed to accept invitation. It may have expired or already been used.");
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-emerald-500 border-r-transparent" />
          <p className="mt-3 text-sm text-slate-400">Verifying session and invitation...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-lg items-center justify-center px-4 py-12">
      <div className="w-full rounded-2xl border border-slate-800 bg-slate-900/90 p-8 shadow-2xl backdrop-blur-md">
        <div className="flex flex-col items-center text-center">
          <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl border border-emerald-500/30 bg-emerald-500/10 text-emerald-400 shadow-inner">
            <ShieldCheckIcon size={32} />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Team Member Invitation</h1>
          <p className="mt-2 text-sm text-slate-400">
            Join the organization on CodeSecAudit AI to access audit logs, repository telemetry, and pull request review gates.
          </p>
        </div>

        {!token ? (
          <div className="mt-6 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-center">
            <div className="flex items-center justify-center gap-2 text-red-400">
              <AlertTriangleIcon size={18} />
              <span className="font-semibold text-sm">Invalid Invitation Link</span>
            </div>
            <p className="mt-1 text-xs text-red-300">
              No secure token was found in the link. Please ask your administrator to re-send the invitation link.
            </p>
            <div className="mt-4">
              <Link href="/login">
                <Button variant="secondary" size="sm">Go to Login</Button>
              </Link>
            </div>
          </div>
        ) : !user ? (
          <div className="mt-6 space-y-4">
            <div className="rounded-xl border border-blue-500/30 bg-blue-500/10 p-4 text-center text-xs text-blue-200">
              You must be logged in to accept this invitation. Sign in with GitHub or your account to proceed.
            </div>
            <Link
              href={`/login?redirect=${encodeURIComponent(`/invite/accept?token=${token}`)}`}
              className="block w-full"
            >
              <Button variant="primary" className="w-full flex items-center justify-center gap-2">
                <GitHubIcon size={16} /> Sign in to Accept Invitation
              </Button>
            </Link>
          </div>
        ) : success ? (
          <div className="mt-6 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-5 text-center">
            <h3 className="text-base font-semibold text-emerald-400">Invitation Accepted!</h3>
            <p className="mt-1 text-xs text-emerald-200">
              Welcome to the organization! Redirecting you to your dashboard now...
            </p>
            <div className="mt-4">
              <Link href="/dashboard">
                <Button variant="primary" size="sm">Go to Dashboard</Button>
              </Link>
            </div>
          </div>
        ) : (
          <div className="mt-6 space-y-5">
            <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4 text-left">
              <div className="text-xs uppercase tracking-wider text-slate-500">Logged in as</div>
              <div className="mt-1 font-medium text-slate-200">{user.username}</div>
              <div className="text-xs text-slate-400">{user.email || "No email on profile"}</div>
            </div>

            {error && (
              <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-xs text-red-300">
                <div className="flex items-center gap-2 font-semibold text-red-400">
                  <AlertTriangleIcon size={16} /> Error
                </div>
                <div className="mt-1">{error}</div>
              </div>
            )}

            <Button
              variant="primary"
              className="w-full"
              disabled={submitting}
              onClick={handleAccept}
            >
              {submitting ? "Accepting Invitation..." : "Accept Invitation & Join Team"}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function AcceptInvitePage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[60vh] items-center justify-center">
          <p className="text-sm text-slate-400">Loading invitation...</p>
        </div>
      }
    >
      <AcceptInviteContent />
    </Suspense>
  );
}
