type ButtonId = 'draw' | 'finish' | 'undo' | 'cancel' | 'clear' | 'copy' |
  'download' | 'tools-toggle' | 'close-tools' | 'zoom-in' | 'zoom-out' |
  'morocco' | 'fit' | 'satellite' | 'streets' | 'help' | 'close-help' |
  'got-it' | 'farmland-focus';

type ElementId = ButtonId | 'search' | 'search-form' | 'search-results' |
  'farmland-toggle' | 'farmland-status' | 'map' | 'map-error' | 'toast' |
  'vertices' | 'area' | 'selection-state' | 'coordinate-note' |
  'coordinate-content' | 'drawing-actions' | 'draw-description' | 'draw-tip' |
  'tools-panel' | 'cursor-coordinates' | 'help-dialog';

type ElementFor<Id extends ElementId> =
  Id extends ButtonId ? HTMLButtonElement :
  Id extends 'search' | 'farmland-toggle' ? HTMLInputElement :
  Id extends 'search-form' ? HTMLFormElement :
  Id extends 'help-dialog' ? HTMLDialogElement : HTMLElement;

export function element<Id extends ElementId>(id: Id): ElementFor<Id> {
  const result = document.getElementById(id);
  if (!result) throw new Error(`Missing application element: ${id}`);
  return result as ElementFor<Id>;
}
