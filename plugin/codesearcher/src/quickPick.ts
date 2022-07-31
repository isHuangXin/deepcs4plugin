import * as vscode from 'vscode';
import { search } from './search';

//you should register all you quickpick options here
function quickPick() {
	vscode.window.showQuickPick(["codeSearch"])
		.then(async select => {
			if (!select) return;
			if (select == "codeSearch") {
				search();
				return;
			}
		})
}

export {
	quickPick
}