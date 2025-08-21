document.addEventListener('DOMContentLoaded', function() {
    const shapes = document.querySelectorAll('.shape');

    shapes.forEach(shape => {
        shape.addEventListener('click', function() {
            document.querySelectorAll('.shape.highlighted').forEach(s => {
                s.classList.remove('highlighted');
            });

            this.classList.add('highlighted');

            setTimeout(() => {
                this.classList.remove('highlighted');
            }, 2000); 
        });

        shape.ondragstart = function() { return false; };
        shape.onselectstart = function() { return false; };
    });
});