/*
* pixel_to_millimeter.h
*
*  Copyright (C) 2013 Diamond Light Source
*
*  Author: James Parkhurst
*
*  This code is distributed under the BSD license, a copy of which is
*  included in the root directory of this package.
*/
#ifndef DXTBX_MODEL_PIXEL_TO_MILLIMETER_H
#define DXTBX_MODEL_PIXEL_TO_MILLIMETER_H

#include <scitbx/vec2.h>
#include <dxtbx/model/parallax_correction.h>
#include <dxtbx/model/panel_data.h>
#include <dxtbx/error.h>

namespace dxtbx { namespace model {

  using scitbx::vec2;

  /**
   * Base class for the pixel to millimeter strategy
   */
  class PxMmStrategy {
  public:

    /** Virtual desctructor */
    virtual ~PxMmStrategy() {}

    /** @returns the name */
    virtual std::string name() const = 0;

    /**
     * Convert a pixel coordinate to a millimeter coordinate
     * @param panel The panel structure
     * @param xy The (x, y) pixel coordinate
     * @return The (x, y) millimeter coordinate
     */
    virtual vec2<double> to_millimeter(const PanelData &panel,
      vec2<double> xy) const = 0;

    /**
     * Convert a millimeter coordinate to a pixel coordinate
     * @param panel The panel structure
     * @param xy The (x, y) millimeter coordinate
     * @return The (x, y) pixel coordinate
     */
    virtual vec2<double> to_pixel(const PanelData &panel,
      vec2<double> xy) const = 0;
  };

  /**
   * The simple pixel to millimeter strategy. Multiply the pixel coordinate
   * by the pixel size and vice versa.
   */
  class SimplePxMmStrategy : public PxMmStrategy {
  public:

    /** Virtual desctructor */
    virtual ~SimplePxMmStrategy() {}

    /** @returns the name */
    virtual std::string name() const {
      return "SimplePxMmStrategy";
    }

    /**
     * Convert a pixel coordinate to a millimeter coordinate
     * @param panel The panel structure
     * @param xy The (x, y) pixel coordinate
     * @return The (x, y) millimeter coordinate
     */
    vec2<double> to_millimeter(const PanelData &panel,
        vec2<double> xy) const {
      vec2<double> pixel_size = panel.get_pixel_size();
      return vec2<double> (xy[0] * pixel_size[0], xy[1] * pixel_size[1]);
    }

    /**
     * Convert a millimeter coordinate to a pixel coordinate
     * @param panel The panel structure
     * @param xy The (x, y) millimeter coordinate
     * @return The (x, y) pixel coordinate
     */
    vec2<double> to_pixel(const PanelData &panel,
        vec2<double> xy) const {
      vec2<double> pixel_size = panel.get_pixel_size();
      return vec2<double> (xy[0] / pixel_size[0], xy[1] / pixel_size[1]);
    }
  };

  /**
   * The parallax corrected strategy. From the simple conversion, then
   * perform a parallax correction.
   */
  class ParallaxCorrectedPxMmStrategy : public SimplePxMmStrategy {
  public:
    ParallaxCorrectedPxMmStrategy(double mu, double t0)
      : mu_(mu),
        t0_(t0) {
      DXTBX_ASSERT(mu > 0);
      DXTBX_ASSERT(t0 > 0);
    }

    /** Virtual desctructor */
    virtual ~ParallaxCorrectedPxMmStrategy() {}

    /** @returns the name */
    virtual std::string name() const {
      return "ParallaxCorrectedPxMmStrategy";
    }

    /** @returns the linear attenuation coefficient (mm^-1) */
    double mu() const {
      return mu_;
    }

    /** @returns the sensor thickness (mm) */
    double t0() const {
      return t0_;
    }

    /**
     * Convert a pixel coordinate to a millimeter coordinate
     * @param panel The panel structure
     * @param xy The (x, y) pixel coordinate
     * @return The (x, y) millimeter coordinate
     */
    vec2<double> to_millimeter(const PanelData &panel,
        vec2<double> xy) const {
      return parallax_correction_inv2(
          mu_, t0_,
          SimplePxMmStrategy::to_millimeter(panel, xy),
          panel.get_fast_axis(),
          panel.get_slow_axis(),
          panel.get_origin());
    }

    /**
     * Convert a millimeter coordinate to a pixel coordinate
     * @param panel The panel structure
     * @param xy The (x, y) millimeter coordinate
     * @return The (x, y) pixel coordinate
     */
    vec2<double> to_pixel(const PanelData &panel,
        vec2<double> xy) const {
      return SimplePxMmStrategy::to_pixel(panel,
        parallax_correction2(
          mu_, t0_,
          xy,
          panel.get_fast_axis(),
          panel.get_slow_axis(),
          panel.get_origin()));
    }

  protected:
    double mu_;
    double t0_;
  };

  /**
   * The parallax corrected strategy with offset applied.
   */
  class OffsetParallaxCorrectedPxMmStrategy : public ParallaxCorrectedPxMmStrategy {
  public:
    OffsetParallaxCorrectedPxMmStrategy(
          double mu,
          double t0,
          scitbx::af::const_ref< double, scitbx::af::c_grid<2> > dx,
          scitbx::af::const_ref< double, scitbx::af::c_grid<2> > dy)
      : ParallaxCorrectedPxMmStrategy(mu, t0),
        dx_(dx.accessor()),
        dy_(dy.accessor()) {
      DXTBX_ASSERT(mu > 0);
      DXTBX_ASSERT(t0 > 0);
      DXTBX_ASSERT(dx_.accessor().all_eq(dy.accessor()));
      std::copy(dx.begin(), dx.end(), dx_.begin());
      std::copy(dy.begin(), dy.end(), dy_.begin());
    }

    /** Virtual desctructor */
    virtual ~OffsetParallaxCorrectedPxMmStrategy() {}

    /** @returns the name */
    virtual std::string name() const {
      return "OffsetParallaxCorrectedPxMmStrategy";
    }

    /** @returns the x correction */
    scitbx::af::versa< double, scitbx::af::c_grid<2> > dx() const {
      return dx_;
    }

    /** @returns the y correction */
    scitbx::af::versa< double, scitbx::af::c_grid<2> > dy() const {
      return dy_;
    }

    /**
     * Convert a pixel coordinate to a millimeter coordinate
     * @param panel The panel structure
     * @param xy The (x, y) pixel coordinate
     * @return The (x, y) millimeter coordinate
     */
    vec2<double> to_millimeter(const PanelData &panel,
        vec2<double> xy) const {

      // Do the naive mapping
      vec2<double> mm = ParallaxCorrectedPxMmStrategy::to_millimeter(panel, xy);

      // Apply the correction
      int i = (int)std::floor(xy[0]);
      int j = (int)std::floor(xy[1]);
      if (i < 0) i = 0;
      if (j < 0) j = 0;
      if (i >= dx_.accessor()[1]) i = dx_.accessor()[1]-1;
      if (j >= dx_.accessor()[0]) j = dx_.accessor()[0]-1;
      double dx = dx_(j,i);
      double dy = dy_(j,i);
      mm[0] -= dx;
      mm[1] -= dy;

      // Return the mapping
      return mm;
    }

    /**
     * Convert a millimeter coordinate to a pixel coordinate
     * @param panel The panel structure
     * @param xy The (x, y) millimeter coordinate
     * @return The (x, y) pixel coordinate
     */
    vec2<double> to_pixel(const PanelData &panel,
        vec2<double> xy) const {
      DXTBX_ASSERT(dx_.accessor().all_eq(dy_.accessor()));
      DXTBX_ASSERT(dx_.accessor()[0] == panel.get_image_size()[1]);
      DXTBX_ASSERT(dx_.accessor()[1] == panel.get_image_size()[0]);

      // Do a naive mapping first
      vec2<double> px = ParallaxCorrectedPxMmStrategy::to_pixel(panel, xy);

      // Apply the correction
      int i = (int)std::floor(px[0]);
      int j = (int)std::floor(px[1]);
      if (i < 0) i = 0;
      if (j < 0) j = 0;
      if (i >= dx_.accessor()[1]) i = dx_.accessor()[1]-1;
      if (j >= dx_.accessor()[0]) j = dx_.accessor()[0]-1;
      double dx = dx_(j,i);
      double dy = dy_(j,i);
      xy[0] += dx;
      xy[1] += dy;

      // Do the parallax correction again
      return ParallaxCorrectedPxMmStrategy::to_pixel(panel, xy);
    }

  protected:
    scitbx::af::versa< double, scitbx::af::c_grid<2> > dx_;
    scitbx::af::versa< double, scitbx::af::c_grid<2> > dy_;
  };

}} // namespace dxtbx::model

#endif /* DXTBX_MODEL_PIXEL_TO_MILLIMETER_H */
