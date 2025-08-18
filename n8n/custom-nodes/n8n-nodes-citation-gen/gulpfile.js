const path = require('path');
const fs = require('fs');
const { task, src, dest } = require('gulp');

task('build:icons', copyIcons);

function copyIcons() {
	const nodeSource = path.resolve('nodes', '**', '*.{png,svg}');
	const nodeDestination = path.resolve('dist', 'nodes');

	src(nodeSource).pipe(dest(nodeDestination));

	// Only copy credentials icons if credentials directory exists
	const credPath = path.resolve('credentials');
	if (fs.existsSync(credPath)) {
		const credSource = path.resolve('credentials', '**', '*.{png,svg}');
		const credDestination = path.resolve('dist', 'credentials');
		return src(credSource).pipe(dest(credDestination));
	}
	
	// Return the node icons stream if no credentials
	return src(nodeSource).pipe(dest(nodeDestination));
}