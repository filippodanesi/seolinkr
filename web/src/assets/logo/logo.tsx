const Logo = () => {
  return (
    <div className="flex items-center gap-2.5">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/logo.svg" alt="SEOLinkr" className="size-7" />
      <div className="flex flex-col gap-0.5 leading-none">
        <span className="font-medium text-sm">SEOLinkr</span>
        <span className="text-[10px] text-muted-foreground">v0.4.0</span>
      </div>
    </div>
  );
};

export default Logo;
