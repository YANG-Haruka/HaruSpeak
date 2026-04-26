"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { SceneSelector } from "@/components/SceneSelector";
import { CustomSceneModal } from "@/components/CustomSceneModal";
import { TopNav } from "@/components/TopNav";
import { useSessionStore } from "@/lib/store";
import { useT } from "@/lib/i18n";
import {
  fetchScenes,
  type SceneMeta,
  type CustomScene,
} from "@/lib/api";

export default function ScenePage() {
  const router = useRouter();
  const t = useT();
  const {
    l1, l2,
    setSceneId,
    setCustomScene,
  } = useSessionStore();
  const [scenes, setScenes] = useState<SceneMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [sceneModal, setSceneModal] = useState(false);

  useEffect(() => {
    if (!l2) {
      router.replace("/");
      return;
    }
    fetchScenes(l2)
      .then(setScenes)
      .finally(() => setLoading(false));
  }, [l2, router]);

  const pickScene = (sceneId: string) => {
    setCustomScene(null);
    setSceneId(sceneId);
    router.push("/chat");
  };

  const submitCustomScene = (s: CustomScene) => {
    setCustomScene(s);
    setSceneId("__custom__");
    setSceneModal(false);
    router.push("/chat");
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
          <SceneSelector
            scenes={scenes}
            l2={l2}
            onPick={pickScene}
            onCustom={() => setSceneModal(true)}
          />
        )}
      </main>

      {sceneModal && (
        <CustomSceneModal
          onCancel={() => setSceneModal(false)}
          onSubmit={submitCustomScene}
        />
      )}
    </>
  );
}
