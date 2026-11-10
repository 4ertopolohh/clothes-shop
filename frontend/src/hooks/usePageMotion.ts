import { useEffect } from "react";
import { cx } from "../components/ui";

// Animate committed content without remounting routes, providers or data loaders.
export function usePageMotion(pathname: string) {
  useEffect(() => {
    const main = document.getElementById("main");
    if (!main) return;
    const media = matchMedia("(prefers-reduced-motion: reduce)");
    const animations = new Set<Animation>();
    const seen = new WeakSet<Element>();
    const visuals = new Set<HTMLElement>();
    const observed = new WeakSet<Element>();
    let frame = 0;
    const blockObserver =
      "IntersectionObserver" in window
        ? new IntersectionObserver(
            (entries) => {
              entries.forEach((entry) => {
                if (!entry.isIntersecting || media.matches) return;
                const node = entry.target as HTMLElement;
                blockObserver?.unobserve(node);
                const calm = /^\/(checkout|order|payment)/.test(pathname);
                const animation = node.animate?.(
                  [
                    { opacity: 0.65, translate: `0 ${calm ? 6 : 16}px` },
                    { opacity: 1, translate: "0 0" },
                  ],
                  {
                    duration: calm ? 240 : 420,
                    easing: "cubic-bezier(.2,.75,.25,1)",
                  },
                );
                if (animation) {
                  animations.add(animation);
                  animation.onfinish = () => animations.delete(animation);
                }
              });
            },
            { threshold: 0.08 },
          )
        : null;
    const run = () => {
      if (media.matches) return;
      main
        .querySelectorAll<HTMLElement>(`.${cx("parallax")}`)
        .forEach((node) => {
          if (!observed.has(node)) {
            observed.add(node);
            observer?.observe(node);
          }
        });
      const selector = [
        "content-page",
        "detail-info",
        "detail-visual",
        "field",
        "order-summary",
        "receipt-items",
      ]
        .map((name) => `.${cx(name)}`)
        .join(",");
      main.querySelectorAll<HTMLElement>(selector).forEach((node) => {
        if (seen.has(node) || node.closest('[role="alert"]')) return;
        seen.add(node);
        blockObserver?.observe(node);
      });
    };
    const update = () => {
      frame = 0;
      if (media.matches) return;
      const depth = innerWidth < 768 ? 10 : 32;
      visuals.forEach((node) => {
        const rect = node.getBoundingClientRect();
        const progress = Math.max(
          -1,
          Math.min(
            1,
            (innerHeight / 2 - rect.top - rect.height / 2) /
              (innerHeight / 2 + rect.height / 2),
          ),
        );
        node.style.setProperty("--parallax-y", `${progress * depth}px`);
      });
    };
    const schedule = () => {
      if (!frame && !media.matches) frame = requestAnimationFrame(update);
    };
    const observer =
      "IntersectionObserver" in window
        ? new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
              if (entry.isIntersecting)
                visuals.add(entry.target as HTMLElement);
              else visuals.delete(entry.target as HTMLElement);
            });
            schedule();
          })
        : null;
    const mutation = new MutationObserver(run);
    mutation.observe(main, { childList: true, subtree: true });
    const preference = () => {
      if (media.matches) {
        animations.forEach((a) => a.cancel());
        visuals.forEach((n) => n.style.removeProperty("--parallax-y"));
      } else {
        run();
        schedule();
      }
    };
    run();
    const entrance =
      !media.matches &&
      main.animate?.([{ opacity: 0.6 }, { opacity: 1 }], {
        duration: 300,
        easing: "ease-out",
      });
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule, { passive: true });
    media.addEventListener("change", preference);
    return () => {
      mutation.disconnect();
      observer?.disconnect();
      blockObserver?.disconnect();
      cancelAnimationFrame(frame);
      entrance && entrance.cancel();
      animations.forEach((a) => a.cancel());
      visuals.forEach((n) => n.style.removeProperty("--parallax-y"));
      window.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
      media.removeEventListener("change", preference);
    };
  }, [pathname]);
}
