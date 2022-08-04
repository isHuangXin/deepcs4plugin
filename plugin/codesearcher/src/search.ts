import * as vscode from 'vscode';
import CodeFetcher from './CodeFetcher';

// this function will call deepcs model server and show some snippets 
// and then insert one under the comment line
async function search() {
	let editor = vscode.window.activeTextEditor;
	let cursor = editor?.selection.active;
	let line = cursor?.line == undefined ? 0 : cursor.line;

	let lineDocument = editor?.document.lineAt(line);
	let configuration = vscode.workspace.getConfiguration("codesearcher");
	let domain: string = configuration.get("queryDomain") as string;
	let port: number = configuration.get("queryPort") as number;
	let fetcher = new CodeFetcher(domain, port);
	let lineText = lineDocument?.text as string;

	lineText = lineText.substring(lineText.lastIndexOf('/') + 1);

	await fetcher.fetchCode(lineText, 5)
		.then(async array => {
			let select: string[] = [];
			array.forEach(element => {
				select.push(`${element[1]}: ${element[0]}`);
			});
			let text = await vscode.window.showQuickPick(select)
				.then(selected => {
					if (!select) return;
					let index = selected?.indexOf(":") as number;
					return selected?.substring(index + 2) as string;
				});
			return text;
		}).then(async text => {
			if (!text) return;
			editor?.edit(edit => {
				edit.insert(new vscode.Position(line + 1, 0), text);
			});
			await vscode.commands.executeCommand("editor.action.formatDocument", editor?.document.uri);
		});
}

export {
	search
}