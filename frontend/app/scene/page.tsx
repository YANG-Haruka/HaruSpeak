"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { SceneSelector } from "@/components/SceneSelector";
import { PersonaSelector } from "@/components/PersonaSelector";
import { CustomSceneModal } from "@/components/CustomSceneModal";
import { CustomPersonaModal } from "@/components/CustomPersonaModal";
import { TopNav } from "@/components/TopNav";
import { useSessionStore } from "@/lib/store";
import { useT } from "@/lib/i18n";
import {
  fetchScenes,
  fetchPersonas,
  type SceneMeta,
  type PersonaMeta,
  type CustomScene,
  type PersonaOverride,
} from "@/lib/api";

export default function ScenePage() {
  const router = useRouter();
  const t = useT();
  const {
    l1, l2,
    setSceneId,
    setCustomScene,
    setPersonaOverride,
    personaOverride,
  } = useSessionStore();
  const [scenes, setScenes] = useState<SceneMeta[]>([]);
  const [personas, setPersonas] = useState<PersonaMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [sceneModal, setSceneModal] = useState(false);
  const [personaModal, setPersonaModal] = useState(false);

  useEffect(() => {
    if (!l2) {
      router.replace("/");
      return;
    }
    Promise.all([fetchScenes(l2), fetchPersonas(l2)])
      .then(([s, p]) => {
        setScenes(s);
        setPersonas(p);
      })
      .finally(() => setLoading(false));
  }, [l2, router]);

  const pickScene = (sceneId: string) => {
    setCustomScene(null);
    setSceneId(sceneId);
    router.push("/chat");
  };

  const pickPersona = (p: PersonaMeta | null) => {
    // null means "no override" — clears any previous selection
    setPersonaOverride(p ? { id: p.id, name: p.name, description: p.description, tone_hint: p.tone_hint } : null);
  };

  const submitCustomScene = (s: CustomScene) => {
    setCustomScene(s);
    setSceneId("__custom__");
    setSceneModal(false);
    router.push("/chat");
  };

  const submitCustomPersona = (p: PersonaOverride) => {
    setPersonaOverride(p);
    setPersonaModal(false);
  };

  if (!l1 || !l2) return null;

  return (
    <>
      <TopNav back />
      <main className="max-w-readable mx-auto px-5 pt-8 pb-14 space-y-10">
        <h2 className="text-[22px] font-semibold tracking-tight">
          {t("choose_scene")}
        </h2>

        {loading && <p className="text-muted text-[14px]">{t("loading")}</p>}

        {!loading && (
          <>
            <SceneSelector
              scenes={scenes}
              l2={l2}
              onPick={pickScene}
              onCustom={() => setSceneModal(true)}
            />

            <PersonaSelector
              personas={personas}
              selectedId={personaOverride?.id ?? null}
              onPick={pickPersona}
              onCustom={() => setPersonaModal(true)}
            />
          </>
        )}
      </main>

      {sceneModal && (
        <CustomSceneModal
          onCancel={() => setSceneModal(false)}
          onSubmit={submitCustomScene}
        />
      )}
      {personaModal && (
        <CustomPersonaModal
          onCancel={() => setPersonaModal(false)}
          onSubmit={submitCustomPersona}
        />
      )}
    </>
  );
}
