import { FileSearch } from "lucide-react";

const Logo = () => {
  return (
    <div className="flex items-center gap-2.5">
      <div className="flex aspect-square size-8 items-center justify-center rounded-sm bg-primary">
        <FileSearch className="size-5 text-primary-foreground" />
      </div>
      <div className="flex flex-col gap-0.5 leading-none">
        <span className="font-medium text-sm">SEO Linker</span>
        <span className="text-xs text-muted-foreground">v0.4.0</span>
      </div>
    </div>
  );
};

export default Logo;
