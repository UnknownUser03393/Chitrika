import { useCallback, useEffect, useRef, useState } from "react";
import { LanguageProvider, useLang } from "./LanguageContext";
import { translations } from "./i18n";
import { HeroSection } from "./HeroSection";
import { ProductShowcase } from "./ProductShowcase";
import { TimelineSection } from "./TimelineSection";
import { ComparisonSection } from "./ComparisonSection";
import { FeaturesSection } from "./FeaturesSection";
import { TestimonialSection } from "./TestimonialSection";
import { FooterSection } from "./FooterSection";
import { usePrefersReducedMotion } from "./usePrefersReducedMotion";
import { useSectionPager } from "./useSectionPager";

interface Props {
  onGetStarted: () => void;
}

const SECTION_IDS = [
  "hero",
  "showcase",
  "timeline",
  "comparison",
  "features",
  "testimonials",
  "footer",
] as const;

const TIMELINE_INDEX = SECTION_IDS.indexOf("timeline");
const PROMO_SECTION_DURATIONS_MS = [7000, 6200, 7800, 5600, 7800, 6800] as const;

function LangToggle() {
  const { lang, toggle } = useLang();
  return (
    <button
      onClick={toggle}
      className="fixed top-4 right-4 z-50 px-3 py-1.5 rounded-full text-xs font-semibold border transition-all hover:scale-105 active:scale-95"
      style={{
        background: "color-mix(in srgb, var(--app-panel) 90%, transparent)",
        borderColor: "var(--app-border)",
        color: "var(--app-accent)",
        backdropFilter: "blur(8px)",
      }}
    >
      {translations.toggle[lang]}
    </button>
  );
}

function SectionDots({
  index,
  onSelect,
}: {
  index: number;
  onSelect: (i: number) => void;
}) {
  const { lang } = useLang();
  const p = translations.pager;

  return (
    <nav
      aria-label={p.nav[lang]}
      className="fixed right-4 top-1/2 -translate-y-1/2 z-50 flex flex-col gap-2.5"
    >
      {SECTION_IDS.map((id, i) => {
        const label = p.sections[id][lang];
        const isActive = i === index;
        return (
          <button
            key={id}
            type="button"
            aria-label={label}
            aria-current={isActive ? "true" : undefined}
            title={label}
            onClick={() => onSelect(i)}
            className="group relative flex items-center justify-end"
          >
            <span
              className="pointer-events-none absolute right-5 whitespace-nowrap rounded-md px-2 py-0.5 text-[11px] font-medium opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100"
              style={{
                background: "var(--app-panel-strong)",
                color: "var(--app-muted)",
                border: "1px solid var(--app-border)",
              }}
            >
              {label}
            </span>
            <span
              className="block rounded-full transition-all"
              style={{
                width: isActive ? 10 : 7,
                height: isActive ? 10 : 7,
                background: isActive ? "var(--app-accent)" : "var(--app-border)",
                boxShadow: isActive
                  ? "0 0 0 3px color-mix(in srgb, var(--app-accent) 25%, transparent)"
                  : "none",
              }}
            />
          </button>
        );
      })}
    </nav>
  );
}

function FreeScrollLanding({ onGetStarted }: Props) {
  const timelineRef = useRef<HTMLDivElement>(null);
  const reduce = usePrefersReducedMotion();
  const promo = false;

  const scrollToTimeline = () => {
    timelineRef.current?.scrollIntoView({ behavior: reduce ? "auto" : "smooth" });
  };

  return (
    <div className="h-full w-full overflow-y-auto">
      <LangToggle />
      <HeroSection onGetStarted={onGetStarted} onScrollToTimeline={scrollToTimeline} />
      <ProductShowcase />
      <div ref={timelineRef}>
        <TimelineSection />
      </div>
      <ComparisonSection />
      <FeaturesSection />
      <TestimonialSection />
      <FooterSection onGetStarted={onGetStarted} promo={promo} />
    </div>
  );
}

function PagedLanding({ onGetStarted }: Props) {
  const [index, setIndex] = useState(0);
  const [direction, setDirection] = useState<1 | -1>(1);
  const slideRefs = useRef<(HTMLDivElement | null)[]>([]);
  const promo = false;

  const onChange = useCallback((next: number, dir: 1 | -1) => {
    setDirection(dir);
    setIndex(next);
    // Reset inner scroll when switching slides
    const el = slideRefs.current[next];
    if (el) el.scrollTop = 0;
  }, []);

  const getActiveScrollEl = useCallback(
    () => slideRefs.current[index] ?? null,
    [index],
  );

  const { go } = useSectionPager({
    enabled: true,
    count: SECTION_IDS.length,
    index,
    onChange,
    getActiveScrollEl,
  });

  useEffect(() => {
    if (!promo || index >= SECTION_IDS.length - 1) return;

    let scrollFrame = 0;
    let scrollDelay = 0;
    const activeSection = SECTION_IDS[index];

    if (activeSection === "timeline") {
      scrollDelay = window.setTimeout(() => {
        const element = slideRefs.current[index];
        if (!element) return;

        const maxScroll = Math.max(0, element.scrollHeight - element.clientHeight);
        const startedAt = performance.now();
        const scrollDuration = 5600;

        const step = (now: number) => {
          const progress = Math.min((now - startedAt) / scrollDuration, 1);
          const eased = progress * progress * (3 - 2 * progress);
          element.scrollTop = maxScroll * eased;
          if (progress < 1) scrollFrame = window.requestAnimationFrame(step);
        };

        scrollFrame = window.requestAnimationFrame(step);
      }, 650);
    }

    const pageTimeout = window.setTimeout(
      () => go(index + 1),
      PROMO_SECTION_DURATIONS_MS[index] ?? 5600,
    );
    return () => {
      window.clearTimeout(pageTimeout);
      window.clearTimeout(scrollDelay);
      window.cancelAnimationFrame(scrollFrame);
    };
  }, [go, index, promo]);

  const goToTimeline = () => go(TIMELINE_INDEX);

const { lang } = useLang();
  const scrollHint = translations.pager.scrollHint[lang];

  return (
    <div className="h-full w-full relative overflow-hidden">
      <LangToggle />
      <SectionDots index={index} onSelect={(i) => go(i)} />

      {SECTION_IDS.map((id, i) => {
        const active = i === index;
        // Exit upward when leaving for a later slide; exit downward when going back
        const offset =
          i === index ? 0 : direction > 0 ? (i < index ? -32 : 32) : i > index ? 32 : -32;

        return (
          <div
            key={id}
            ref={(el) => {
              slideRefs.current[i] = el;
              if (el) {
                if (active) el.removeAttribute("inert");
                else el.setAttribute("inert", "");
              }
            }}
            className="absolute inset-0 overflow-y-auto"
            style={{
              opacity: active ? 1 : 0,
              transform: `translateY(${offset}px)`,
              transition:
                "opacity 0.45s cubic-bezier(0.25, 0.46, 0.45, 0.94), transform 0.45s cubic-bezier(0.25, 0.46, 0.45, 0.94)",
              pointerEvents: active ? "auto" : "none",
              zIndex: active ? 2 : 0,
            }}
            aria-hidden={!active}
          >
            {id === "hero" && (
              <HeroSection
                onGetStarted={onGetStarted}
                onScrollToTimeline={goToTimeline}
              />
            )}
            {id === "showcase" && <ProductShowcase active={active} />}
            {id === "timeline" && <TimelineSection active={active} />}
            {id === "comparison" && <ComparisonSection active={active} />}
            {id === "features" && <FeaturesSection active={active} autoPlay={promo} />}
            {id === "testimonials" && <TestimonialSection active={active} />}
            {id === "footer" && (
              <FooterSection onGetStarted={onGetStarted} active={active} promo={promo} />
            )}
          </div>
        );
      })}

      {index === 0 && (
        <div
          className="pointer-events-none fixed bottom-6 left-1/2 -translate-x-1/2 z-40 text-[11px] tracking-wide uppercase"
          style={{ color: "var(--app-subtle)" }}
          aria-hidden="true"
        >
          {scrollHint}
        </div>
      )}
    </div>
  );
}

function LandingInner({ onGetStarted }: Props) {
  const reduce = usePrefersReducedMotion();

  // Accessibility: free native scroll when reduced motion is requested
  if (reduce) {
    return <FreeScrollLanding onGetStarted={onGetStarted} />;
  }

  return <PagedLanding onGetStarted={onGetStarted} />;
}

export function LandingPage({ onGetStarted }: Props) {
  return (
    <LanguageProvider>
      <LandingInner onGetStarted={onGetStarted} />
    </LanguageProvider>
  );
}
