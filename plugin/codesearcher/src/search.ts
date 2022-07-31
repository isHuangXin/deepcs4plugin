import { text } from 'stream/consumers';
import * as vscode from 'vscode';
import CodeFetcher from './CodeFetcher';

function search() {
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

	fetcher.fetchCode(lineText, 5)
		.then(array => {
			array.forEach(element => {
				console.log(`${element[1]}: ${element[0]}`);
			})
			let text = "";
			return text;
		}).then(async text => {
			editor?.edit(edit => {
				edit.insert(new vscode.Position(line + 1, 0), text);
			})
			await vscode.commands.executeCommand("editor.action.formatDocument", editor?.document.uri);
		})
}

export {
	search
}