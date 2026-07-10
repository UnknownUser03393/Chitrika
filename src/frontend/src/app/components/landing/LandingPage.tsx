import { useRef } from "react";
import { LanguageProvider, useLang } from "./LanguageContext";
import { translations } from "./i18n";
import { HeroSection } from "./HeroSection";
import { ProductShowcase } from "./ProductShowcase";
import { TimelineSection } from "./TimelineSection";
import { ComparisonSection } from "./ComparisonSection";
import { FeaturesSection } from "./FeaturesSection";
import { TestimonialSection } from "./TestimonialSection";
import { FooterSection } from "./FooterSection";

interface Props {
  onGetStarted: () => void;
}

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

function LandingInner({ onGetStarted }: Props) {
  const timelineRef = useRef<HTMLDivElement>(null);

  const scrollToTimeline = () => {
    timelineRef.current?.scrollIntoView({ behavior: "smooth" });
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
      <FooterSection onGetStarted={onGetStarted} />
    </div>
  );
}

export function LandingPage({ onGetStarted }: Props) {
  return (
    <LanguageProvider>
      <LandingInner onGetStarted={onGetStarted} />
    </LanguageProvider>
  );
}
