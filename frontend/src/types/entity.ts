export interface EntityField {
  [fieldId: string]: {
    listLabel?: string;
    type?: string;
    [key: string]: any;
  };
}
