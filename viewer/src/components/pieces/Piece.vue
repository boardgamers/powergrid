<script lang="ts">
import { Vue, Component, Inject, Prop, Watch } from 'vue-property-decorator';
import { EventEmitter } from 'events';
import { PieceType, UIData } from './../../types/ui-data';

@Component({
    created(this: Piece) {
    },
    mounted(this: Piece) {
        this.mounted = true;
    },
    beforeDestroy(this: Piece) {
        this.onTransitionEnd();
    }
})
export default class Piece extends Vue {
    @Prop({ default: () => ({ x: 0, y: 0, scale: 1, rotate: 0 }) })
    targetState!: {
        x: number,
        y: number,
        rotate: number,
        scale: number,
    };

    @Prop()
    pieceId!: string;

    @Prop()
    transparent?: boolean;

    @Inject()
    readonly communicator!: EventEmitter;

    @Inject()
    readonly ui!: UIData;

    public pieceType!: PieceType;

    currentX = 0;
    currentY = 0;
    currentScale = 1;
    mounted = false;
    transitioning = false;
    transitionCount = 0;

    moving = false;

    startTransitioning() {
        if (this.transitioning) {
            return;
        }

        this.ui.waitingAnimations += 1;
        this.transitioning = true;
        this.transitionCount += 1;

        const count = this.transitionCount;

        // Safeguard to make sure even if we don't catch the transition end event, we stop the transition
        setTimeout(() => {
            if (count === this.transitionCount) {
                this.onTransitionEnd();
            }
        }, 1000);
    }

    @Watch('dragging')
    @Watch('targetState', { immediate: true })
    onTargetChanged(newVal: boolean, oldVal: boolean) {
        if (this.targetState.x === this.currentX && this.targetState.y === this.currentY
            && (!this.targetState.scale || this.targetState.scale === this.currentScale)) {
            return;
        }

        if (!this.transitioning && this.mounted) {
            if (!(oldVal && !newVal)) {
                this.startTransitioning();
            } else {
                this.moving = true;
                setTimeout(() => this.moving = false, 800);
            }
        }

        if (!this.mounted) {
            this.currentX = this.targetState.x;
            this.currentY = this.targetState.y;
            this.currentScale = this.targetState.scale ?? 1;
        } else {
            // Make sure the animation plays by waiting until the class "dragging" is removed for sure from the element
            setTimeout(() => {
                this.currentX = this.targetState.x;
                this.currentY = this.targetState.y;
                this.currentScale = this.targetState.scale ?? 1;
            });
        }
    }

    onTransitionEnd() {
        if (this.transitioning) {
            this.transitioning = false;
            this.ui.waitingAnimations = Math.max(this.ui.waitingAnimations - 1, 0);
        }
    }

    get elId() {
        return this.transitioning || this.moving ? 'moving' : undefined;
    }
}
</script>
