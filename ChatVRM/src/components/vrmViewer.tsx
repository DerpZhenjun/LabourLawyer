import { useContext, useEffect, useRef } from "react";
import { ViewerContext } from "../features/vrmViewer/viewerContext";
import { buildUrl } from "@/utils/buildUrl";

type Props = { onReady?: () => void; onError?: () => void };
export default function VrmViewer({ onReady, onError }: Props) {
  const { viewer } = useContext(ViewerContext);
  const canvas = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    if (!canvas.current) return;
    let active = true;
    const element = canvas.current;
    const over = (event: DragEvent) => event.preventDefault();
    const drop = async (event: DragEvent) => {
      event.preventDefault();
      const file = event.dataTransfer?.files[0];
      if (!file || !file.name.toLowerCase().endsWith(".vrm")) return;
      const url = URL.createObjectURL(file);
      try { await viewer.loadVrm(url); if (active) onReady?.(); }
      catch { if (active) onError?.(); }
      finally { URL.revokeObjectURL(url); }
    };
    element.addEventListener("dragover", over); element.addEventListener("drop", drop);
    try {
      viewer.setup(canvas.current);
      viewer.loadVrm(buildUrl("/AvatarSample_B.vrm")).then(() => { if (active) onReady?.(); }).catch(() => { if (active) onError?.(); });
    } catch { onError?.(); }
    return () => { active = false; element.removeEventListener("dragover", over); element.removeEventListener("drop", drop); viewer.dispose(); };
  }, [viewer, onReady, onError]);
  return <div style={{ position: "absolute", inset: 0 }}><canvas ref={canvas} style={{ width: "100%", height: "100%", display: "block" }} /></div>;
}
