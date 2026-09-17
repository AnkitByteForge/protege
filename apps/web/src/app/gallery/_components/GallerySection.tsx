import type { ReactNode } from "react";
import { Heading, Text } from "@/components/primitives/Typography";

export function GallerySection({
  id,
  title,
  description,
  children,
}: {
  id: string;
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <section
      id={id}
      aria-labelledby={`${id}-heading`}
      className="scroll-mt-8 border-t border-sand-300 pt-10"
    >
      <Heading as="h2" id={`${id}-heading`}>
        {title}
      </Heading>
      {description && (
        <Text muted className="mt-1 max-w-2xl">
          {description}
        </Text>
      )}
      <div className="mt-6">{children}</div>
    </section>
  );
}
