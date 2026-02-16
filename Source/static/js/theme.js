(function() {
	var STORAGE_KEY = 'grocery-guru-theme';

	function toggleTheme() {
		var html = document.documentElement;
		var current = html.getAttribute('data-theme') || 'light';
		var next = current === 'dark' ? 'light' : 'dark';
		html.setAttribute('data-theme', next);
		localStorage.setItem(STORAGE_KEY, next);
	}

	// Expose globally for onclick (works even if script loads late)
	window.groceryGuruToggleTheme = toggleTheme;

	// Also bind via JS for accessibility and other toggle instances
	function init() {
		document.querySelectorAll('.js-theme-toggle').forEach(function(btn) {
			btn.addEventListener('click', function(e) {
				e.preventDefault();
				toggleTheme();
			});
		});
	}

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', init);
	} else {
		init();
	}
})();
