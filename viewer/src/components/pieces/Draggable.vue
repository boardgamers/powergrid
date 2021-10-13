<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';

@Component({
    mounted(this: Draggable) {
        this.$nextTick(() => {
            const endDrag = () => this.endDrag();
            const drag = (event: MouseEvent | TouchEvent) => this.drag(event);

            this.htmlElement.addEventListener('mousedown', event => this.startDrag(event));
            this.htmlElement.addEventListener('touchstart', event => this.startDrag(event));

            this.svgElement.addEventListener('touchmove', drag);
            this.svgElement.addEventListener('touchend', endDrag);
            this.svgElement.addEventListener('touchleave', endDrag);
            this.svgElement.addEventListener('touchcancel', endDrag);

            this.$on('hook:beforeDestroy', () => this.svgElement.removeEventListener('touchmove', drag));
            this.$on('hook:beforeDestroy', () => this.svgElement.removeEventListener('touchend', endDrag));
            this.$on('hook:beforeDestroy', () => this.svgElement.removeEventListener('touchleave', endDrag));
            this.$on('hook:beforeDestroy', () => this.svgElement.removeEventListener('touchcancel', endDrag));

            this.svgElement.addEventListener('mouseleave', endDrag);
            this.svgElement.addEventListener('mouseup', endDrag);
            this.svgElement.addEventListener('mousemove', drag);

            this.$on('hook:beforeDestroy', () => this.svgElement.removeEventListener('mouseleave', endDrag));
            this.$on('hook:beforeDestroy', () => this.svgElement.removeEventListener('mouseup', endDrag));
            this.$on('hook:beforeDestroy', () => this.svgElement.removeEventListener('mousemove', drag));
        });
    }
})
export default class Draggable extends Vue {
    @Prop()
    canDrag!: boolean;

    dragging = false;
    _offset = { x: 0, y: 0 };
    _transform?: SVGTransform;
    _dragStart?: number;

    get svgElement() {
        return document.querySelector('#scene') as SVGSVGElement;
    }

    get htmlElement() {
        return this.$el as SVGGElement;
    }

    startDrag(evt: MouseEvent | TouchEvent) {
        if (!this.canDrag)
            return;

        this.dragging = true;

        this._offset = this.getMousePosition(evt);
        // Get all the transforms currently on this element
        const transforms: SVGTransformList = this.htmlElement.transform.baseVal;
        // Ensure the first transform is a translate transform
        if (transforms.numberOfItems === 0 || transforms.getItem(0).type !== SVGTransform.SVG_TRANSFORM_TRANSLATE) {
            // Create an transform that translates by (0, 0)
            const translate = this.svgElement.createSVGTransform();
            translate.setTranslate(0, 0);
            // Add the translation to the front of the transforms list
            this.htmlElement.transform.baseVal.insertItemBefore(translate, 0);
        }

        // Get initial translation amount
        this._transform = transforms.getItem(0);
        this._offset.x -= this._transform.matrix.e;
        this._offset.y -= this._transform.matrix.f;
        this._dragStart = Date.now();
    }

    drag(evt: MouseEvent | TouchEvent) {
        if (!this.dragging) {
            return;
        }

        evt.preventDefault();
        const coord = this.getMousePosition(evt);
        this._transform!.setTranslate(coord.x - this._offset.x, coord.y - this._offset.y);

        this.$emit('draggedTo', { x: coord.x - this._offset.x, y: coord.y - this._offset.y });
    }

    endDrag() {
        this.dragging = false;
        if (Date.now() - this._dragStart! < 100) {
            this.$nextTick(() => { this.$emit('fastClick', this); });
        }
    }

    getMousePosition(evt: MouseEvent | TouchEvent) {
        if ((evt as TouchEvent).touches) {
            evt = (evt as TouchEvent).touches[0] as any;
        }

        const CTM = this.svgElement.getScreenCTM()!;
        return {
            x: ((evt as any).clientX - CTM.e) / CTM.a,
            y: ((evt as any).clientY - CTM.f) / CTM.d
        };
    }
}
</script>
