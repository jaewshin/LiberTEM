import * as React from "react";
import { ReactElement } from "react";
import { connect } from "react-redux";
import { Image } from 'semantic-ui-react';
import { Omit } from "../../helpers/types";
import { RootReducer } from "../../store";
import { JobState } from "../types";

interface JobProps {
    job?: JobState,
    width: number,
    height: number,
}

type ExternalJobProps = Omit<JobProps, "job"> & {
    job: string,
}

interface PlaceholderProps {
    width: number,
    height: number,
}

const PlaceholderImage: React.SFC<PlaceholderProps> = ({ children, width, height }) => {
    const aspect = 100 * (height / width);
    return (
        <div style={{ paddingBottom: `${aspect}%`, width: "100%", position: "relative" }}>
            {
                React.Children.map(children, child => {
                    if (!React.isValidElement(child)) {
                        return child;
                    }
                    return React.cloneElement(child as ReactElement<any>, {
                        style: {
                            position: "absolute",
                            left: 0,
                            top: 0,
                            ...(child.props as any).style,
                        },
                    });
                })
            }
        </div>
    )
}

const JobComponent: React.SFC<JobProps> = ({ job, width, height }) => {
    let msg;
    let imgs = [
        <PlaceholderImage width={width} height={height} key={-1} />
    ];
    if (!job) {
        msg = <p>&nbsp;</p>;
    } else {
        imgs = (job.results.map((res, idx) => {
            return (
                <PlaceholderImage width={width} height={height} key={idx}>
                    <Image style={{ width: "100%", height: "auto", imageRendering: "pixelated" }} src={res.imageURL} width={width} height={height} />
                </PlaceholderImage>
            );
        }))
        if (job.startTimestamp && job.endTimestamp) {
            const dt = (job.endTimestamp - job.startTimestamp) / 1000;
            msg = <p>Analysis done in {dt} seconds</p>;
        } else {
            msg = <p>Analysis running...</p>;
        }
    }
    return (
        <div>
            {imgs}
            {msg}
        </div>
    );
};

const mapStateToProps = (state: RootReducer, ownProps: ExternalJobProps) => {
    return {
        job: ownProps.job ? state.job.byId[ownProps.job] : undefined,
    };
};

export default connect(mapStateToProps)(JobComponent);