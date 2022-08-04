import * as vscode from 'vscode';
import { search } from './search';

//you should register all your quickpick options here
function quickPick() {
	vscode.window.showQuickPick(["codeSearch"])
		.then(async select => {
			if (!select) return;
			// this quickpick option is for model deepcs 
			// and insert code under the comment line
			if (select == "codeSearch") {
				await search();
				return;
			}
		});
}

export {
	quickPick
}