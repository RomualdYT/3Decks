import { useLayoutEffect, useRef, type CSSProperties, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  style: CSSProperties;
}

// Scale the entire native canvas together. WebKit does not reliably scale
// positioned HTML inside an SVG foreignObject, which crops the grid and dock.
export function ConsoleTouchCanvas({ children, style }: Props) {
  const canvasRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const canvas = canvasRef.current;
    const viewport = canvas?.parentElement;
    if (!canvas || !viewport) return;
    let previousScale = -1;
    const resize = (width: number, height: number) => {
      const scale = Math.min(width / 320, height / 240);
      if (scale === previousScale || scale <= 0) return;
      previousScale = scale;
      canvas.style.transform = `scale(${scale})`;
    };
    // Measure the layout box, not the transformed rectangle: modal entrance
    // animations scale ancestors without changing the screen's actual size.
    resize(viewport.clientWidth, viewport.clientHeight);
    const observer = new ResizeObserver(([entry]) => {
      if (entry) resize(entry.contentRect.width, entry.contentRect.height);
    });
    observer.observe(viewport);
    return () => observer.disconnect();
  }, []);

  return <div ref={canvasRef} className="console-touch-canvas" style={style}>{children}</div>;
}
