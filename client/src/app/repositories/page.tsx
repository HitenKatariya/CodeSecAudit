"use client";

import React, { useEffect, useState, useMemo } from "react";
import { Repository } from "@/types";
import { fetchRepositories, getGitHubAppInstallUrl } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { MetricCard } from "@/components/ui/MetricCard";
import { Button } from "@/components/ui/Button";
import { RepositoriesTable } from "@/components/repositories/RepositoriesTable";
import { GitHubIcon } from "@/components/ui/Icons";

export default function RepositoriesPage() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [search, setSearch] = useState("");
  const [selectedLanguage, setSelectedLanguage] = useState("all");

  useEffect(() => {
    fetchRepositories().then((data) => setRepositories(data));
  }, []);

  const totalRepos = repositories.length;
  const protectedRepos = repositories.filter(
    (r) => r.status === "Protected" || r.status === "Passed"
  ).length;
  const avgScore =
    totalRepos > 0
      ? Math.round(
          repositories.reduce((acc, r) => acc + (r.security_score || 0), 0) /
            totalRepos
        )
      : 100;
  const totalOpenFindings = repositories.reduce(
    (acc, r) => acc + (r.open_findings_count || 0),
    0
  );
  const critCount = repositories.reduce(
    (acc, r) => acc + (r.critical_count || 0),
    0
  );
  const highCount = repositories.reduce(
    (acc, r) => acc + (r.high_count || 0),
    0
  );

  const languages = useMemo(() => {
    const set = new Set(repositories.map((r) => r.language).filter(Boolean));
    return ["all", ...Array.from(set)];
  }, [repositories]);

  const filtered = useMemo(() => {
    return repositories.filter((r) => {
      const matchSearch =
        r.name.toLowerCase().includes(search.toLowerCase()) ||
        (r.full_name && r.full_name.toLowerCase().includes(search.toLowerCase()));
      const matchLang =
        selectedLanguage === "all" || r.language === selectedLanguage;
      return matchSearch && matchLang;
    });
  }, [repositories, search, selectedLanguage]);

  return (
    <div className="space-y">
      <PageHeader
        title="Repositories"
        subtitle="Monitored source repositories with automated PR security gates."
        actions={
          <a href={getGitHubAppInstallUrl()} target="_blank" rel="noopener noreferrer">
            <Button
              variant="primary"
              size="md"
              icon={<GitHubIcon size={16} />}
            >
              Connect Repository ↗
            </Button>
          </a>
        }
      />

      {/* 4 Summary stat cards dynamically computed from live repositories */}
      <div className="stat-grid">
        <MetricCard
          label="Monitored Repositories"
          value={String(totalRepos)}
          subtitle="All active branches tracked"
        />

        <MetricCard
          label="Protected Repositories"
          value={`${protectedRepos} / ${totalRepos}`}
          severity={protectedRepos === totalRepos ? "passed" : "warning"}
          subtitle={`${
            totalRepos > 0
              ? Math.round((protectedRepos / totalRepos) * 100)
              : 100
          }% policy enforcement`}
        />

        <MetricCard
          label="Avg Security Score"
          value={String(avgScore)}
          suffix="/ 100"
          severity={avgScore >= 80 ? "passed" : "critical"}
          subtitle="Target: >= 80"
        />

        <MetricCard
          label="Total Active Findings"
          value={String(totalOpenFindings)}
          severity={critCount > 0 ? "critical" : "high"}
          subtitle={`${critCount} critical, ${highCount} high`}
        />
      </div>

      {/* Filter Toolbar */}
      <div className="filter-bar flex-between">
        <div className="flex items-center gap-2.5 flex-wrap">
          <input
            type="text"
            placeholder="Search repositories..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="form-input"
            style={{ width: "240px" }}
          />

          <select
            value={selectedLanguage}
            onChange={(e) => setSelectedLanguage(e.target.value)}
            className="form-input"
          >
            <option value="all">All Languages</option>
            {languages
              .filter((l) => l !== "all")
              .map((lang) => (
                <option key={lang} value={lang}>
                  {lang}
                </option>
              ))}
          </select>
        </div>

        <span className="text-xs text-dim">
          Showing {filtered.length} of {repositories.length} repositories
        </span>
      </div>

      {/* Repositories Table */}
      <RepositoriesTable repositories={filtered} />
    </div>
  );
}
