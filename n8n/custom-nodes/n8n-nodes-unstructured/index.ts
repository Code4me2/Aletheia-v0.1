import { INodeType } from "n8n-workflow";
import { unstructured } from "./nodes/unstructured/unstructured.node";

export const nodeTypes: INodeType[] = [
  new unstructured(),
];
