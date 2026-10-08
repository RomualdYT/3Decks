import type { PageConfig } from "../app/types";
import { ButtonInspector, type ButtonInspectorProps } from "./ButtonInspector";
import { PageInspector } from "./PageInspector";

interface Props extends Omit<ButtonInspectorProps, "button"> {
  page: PageConfig;
  button: ButtonInspectorProps["button"] | null;
  onUpdatePage: (update: (page: PageConfig) => void) => void;
  onDeletePage: () => void;
}

export function Inspector(props: Props) {
  if (props.button) return <ButtonInspector {...props} button={props.button} />;
  return <PageInspector page={props.page} schema={props.schema} locale={props.locale} t={props.t} onUpdatePage={props.onUpdatePage} onDeletePage={props.onDeletePage} />;
}
