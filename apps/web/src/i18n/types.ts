import type { en } from "./messages/en";

/** Same tree as `en`, with every leaf widened to `string`. */
type Widen<T> = { readonly [K in keyof T]: T[K] extends string ? string : Widen<T[K]> };
export type Messages = Widen<typeof en>;

type Paths<T, P extends string = ""> = {
  [K in keyof T & string]: T[K] extends string ? `${P}${K}` : Paths<T[K], `${P}${K}.`>;
}[keyof T & string];

/** Every valid dotted message key, e.g. `"team.inviteTitle"`. */
export type MessageKey = Paths<Messages>;
export type Vars = Record<string, string | number>;
export type Translate = ((key: MessageKey, vars?: Vars) => string) & {
  /** Look up a key built at runtime (e.g. from an API code). Returns undefined if missing. */
  dynamic: (key: string, vars?: Vars) => string | undefined;
};
