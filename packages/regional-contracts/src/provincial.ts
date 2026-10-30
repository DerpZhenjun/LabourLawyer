/** Portable validation result for historical official provincial field contracts. */
export interface ProvincialFieldError {field:string; label:string; message:string}
export interface ProvincialValidation {valid:boolean; errors:ProvincialFieldError[]}
export class ProvincialValidationError extends Error {
  fieldErrors:ProvincialFieldError[]
  constructor(errors:ProvincialFieldError[]){super(errors[0]?.message || '请核对填写内容。');this.fieldErrors=errors}
}
