// Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { getConfig, updateConfig } from "@/lib/api";
import type { AppConfig } from "@/lib/types";

export default function SettingsPage() {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [saving, setSaving] = useState(false);

  // Editable fields
  const [apiKey, setApiKey] = useState("");
  const [defaultModel, setDefaultModel] = useState("");
  const [maxLinks, setMaxLinks] = useState(10);
  const [topN, setTopN] = useState(40);
  const [embeddingModel, setEmbeddingModel] = useState("");
  const [cacheTtl, setCacheTtl] = useState(24);
  const [gscServiceAccount, setGscServiceAccount] = useState("");
  const [gscOauthSecrets, setGscOauthSecrets] = useState("");
  const [gscCacheTtl, setGscCacheTtl] = useState(48);
  const [newSitemapName, setNewSitemapName] = useState("");
  const [newSitemapUrl, setNewSitemapUrl] = useState("");
  const [sitemaps, setSitemaps] = useState<Record<string, string>>({});

  useEffect(() => {
    getConfig()
      .then((c) => {
        setConfig(c);
        setApiKey(c.api_key);
        setDefaultModel(c.default_model);
        setMaxLinks(c.max_links);
        setTopN(c.top_n);
        setEmbeddingModel(c.embedding_model);
        setCacheTtl(c.cache_ttl_hours);
        setGscServiceAccount(c.gsc_service_account);
        setGscOauthSecrets(c.gsc_oauth_secrets);
        setGscCacheTtl(c.gsc_cache_ttl);
        setSitemaps(c.sitemaps);
      })
      .catch((e) => toast.error(String(e)));
  }, []);

  async function handleSave() {
    setSaving(true);
    try {
      await updateConfig({
        api_key: apiKey,
        default_model: defaultModel,
        max_links: maxLinks,
        top_n: topN,
        embedding_model: embeddingModel,
        cache_ttl_hours: cacheTtl,
        gsc_service_account: gscServiceAccount,
        gsc_oauth_secrets: gscOauthSecrets,
        gsc_cache_ttl: gscCacheTtl,
        sitemaps,
      });
      toast.success("Settings saved");
    } catch (e) {
      toast.error(String(e));
    } finally {
      setSaving(false);
    }
  }

  function addSitemap() {
    if (!newSitemapName || !newSitemapUrl) return;
    setSitemaps((prev) => ({ ...prev, [newSitemapName]: newSitemapUrl }));
    setNewSitemapName("");
    setNewSitemapUrl("");
  }

  function removeSitemap(name: string) {
    setSitemaps((prev) => {
      const next = { ...prev };
      delete next[name];
      return next;
    });
  }

  if (!config) return <p className="p-6">Loading...</p>;

  return (
    <div className="space-y-6 p-6">
      {/* General */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">General</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label>Anthropic API Key</Label>
              <Input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Default Model</Label>
              <Input
                value={defaultModel}
                onChange={(e) => setDefaultModel(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Max Links</Label>
              <Input
                type="number"
                value={maxLinks}
                onChange={(e) => setMaxLinks(Number(e.target.value))}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Top N Candidates</Label>
              <Input
                type="number"
                value={topN}
                onChange={(e) => setTopN(Number(e.target.value))}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Embedding Model</Label>
              <Input
                value={embeddingModel}
                onChange={(e) => setEmbeddingModel(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Cache TTL (hours)</Label>
              <Input
                type="number"
                value={cacheTtl}
                onChange={(e) => setCacheTtl(Number(e.target.value))}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* GSC */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Google Search Console</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label>Service Account JSON Path</Label>
              <Input
                value={gscServiceAccount}
                onChange={(e) => setGscServiceAccount(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label>OAuth Client Secrets Path</Label>
              <Input
                value={gscOauthSecrets}
                onChange={(e) => setGscOauthSecrets(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label>GSC Cache TTL (hours)</Label>
              <Input
                type="number"
                value={gscCacheTtl}
                onChange={(e) => setGscCacheTtl(Number(e.target.value))}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Sitemaps */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Saved Sitemaps</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {Object.entries(sitemaps).map(([name, url]) => (
            <div key={name} className="flex items-center gap-2 text-sm">
              <span className="font-medium">{name}:</span>
              <span className="flex-1 truncate text-muted-foreground">
                {url}
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => removeSitemap(name)}
              >
                Remove
              </Button>
            </div>
          ))}
          <Separator />
          <div className="flex gap-2">
            <Input
              placeholder="Name"
              value={newSitemapName}
              onChange={(e) => setNewSitemapName(e.target.value)}
              className="w-32"
            />
            <Input
              placeholder="https://example.com/sitemap.xml"
              value={newSitemapUrl}
              onChange={(e) => setNewSitemapUrl(e.target.value)}
              className="flex-1"
            />
            <Button variant="secondary" onClick={addSitemap}>
              Add
            </Button>
          </div>
        </CardContent>
      </Card>

      <Button onClick={handleSave} disabled={saving}>
        {saving ? "Saving..." : "Save Settings"}
      </Button>
    </div>
  );
}
