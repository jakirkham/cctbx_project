/* Copyright (c) 2001-2002 The Regents of the University of California
   through E.O. Lawrence Berkeley National Laboratory, subject to
   approval by the U.S. Department of Energy.
   See files COPYRIGHT.txt and LICENSE.txt for further details.

   Revision history:
     2002 Aug: Copied from cctbx/bpl_utils.h (R.W. Grosse-Kunstleve)
     2001 Apr: SourceForge release (R.W. Grosse-Kunstleve)
 */

#ifndef SCITBX_BOOST_PYTHON_CONTAINER_CONVERSIONS_H
#define SCITBX_BOOST_PYTHON_CONTAINER_CONVERSIONS_H

#include <boost/python/list.hpp>
#include <boost/python/tuple.hpp>
#include <boost/python/extract.hpp>

namespace scitbx { namespace boost_python { namespace container_conversions {

  template <typename ContainerType>
  struct to_tuple
  {
    static PyObject* convert(ContainerType const& a)
    {
      using namespace boost::python;
      list result;
      for(std::size_t i=0;i<a.size();i++) {
        result.append(object(a[i]));
      }
      return incref(tuple(result).ptr());
    }
  };

  struct default_policy
  {
    static bool check_convertibility_per_element() { return false; }

    template <typename ContainerType>
    static bool check_size(boost::type<ContainerType>, std::size_t sz)
    {
      return true;
    }

    template <typename ContainerType>
    static void assert_size(boost::type<ContainerType>, std::size_t sz) {}

    template <typename ContainerType>
    static void reserve(ContainerType& a, std::size_t sz) {}
  };

  struct fixed_size_policy
  {
    static bool check_convertibility_per_element() { return true; }

    template <typename ContainerType>
    static bool check_size(boost::type<ContainerType>, std::size_t sz)
    {
      return ContainerType::size() == sz;
    }

    template <typename ContainerType>
    static void assert_size(boost::type<ContainerType>, std::size_t sz)
    {
      if (!check_size(boost::type<ContainerType>(), sz)) {
        PyErr_SetString(PyExc_RuntimeError,
          "Insufficient elements for fixed-size array.");
        boost::python::throw_error_already_set();
      }
    }

    template <typename ContainerType>
    static void reserve(ContainerType& a, std::size_t sz)
    {
      if (sz > ContainerType::size()) {
        PyErr_SetString(PyExc_RuntimeError,
          "Too many elements for fixed-size array.");
        boost::python::throw_error_already_set();
      }
    }

    template <typename ContainerType, typename ValueType>
    static void set_value(ContainerType& a, std::size_t i, ValueType const& v)
    {
      reserve(a, i+1);
      a[i] = v;
    }
  };

  struct variable_capacity_policy : default_policy
  {
    template <typename ContainerType>
    static void reserve(ContainerType& a, std::size_t sz)
    {
      a.reserve(sz);
    }

    template <typename ContainerType, typename ValueType>
    static void set_value(ContainerType& a, std::size_t i, ValueType const& v)
    {
      assert(a.size() == i);
      a.push_back(v);
    }
  };

  struct fixed_capacity_policy : variable_capacity_policy
  {
    template <typename ContainerType>
    static bool check_size(boost::type<ContainerType>, std::size_t sz)
    {
      return ContainerType::max_size() >= sz;
    }
  };

  struct linked_list_policy : default_policy
  {
    template <typename ContainerType, typename ValueType>
    static void set_value(ContainerType& a, std::size_t i, ValueType const& v)
    {
      a.push_back(v);
    }
  };

  template <typename ContainerType, typename ConversionPolicy>
  struct from_python_sequence
  {
    typedef typename ContainerType::value_type container_element_type;

    from_python_sequence()
    {
      boost::python::converter::registry::push_back(
        &convertible,
        &construct,
        boost::python::type_id<ContainerType>());
    }

    static void* convertible(PyObject* obj_ptr)
    {
      using namespace boost::python;
      {
        // Restriction to list, tuple, iter, xrange until
        // Boost.Python overload resolution is enhanced.
        if (!(   PyList_Check(obj_ptr)
              || PyTuple_Check(obj_ptr)
              || PyIter_Check(obj_ptr)
              || PyRange_Check(obj_ptr))) return 0;
      }
      handle<> obj_iter(allow_null(PyObject_GetIter(obj_ptr)));
      if (!obj_iter.get()) { // must be convertible to an iterator
        PyErr_Clear();
        return 0;
      }
      if (ConversionPolicy::check_convertibility_per_element()) {
        int obj_size = PyObject_Length(obj_ptr);
        if (obj_size < 0) { // must be a measurable sequence
          PyErr_Clear();
          return 0;
        }
        if (!ConversionPolicy::check_size(
          boost::type<ContainerType>(), obj_size)) return 0;
        bool is_range = PyRange_Check(obj_ptr);
        std::size_t i=0;
        for(;;i++) {
          handle<> py_elem_hdl(allow_null(PyIter_Next(obj_iter.get())));
          if (PyErr_Occurred()) {
            PyErr_Clear();
            return 0;
          }
          if (!py_elem_hdl.get()) break; // end of iteration
          object py_elem_obj(py_elem_hdl);
          extract<container_element_type> elem_proxy(py_elem_obj);
          if (!elem_proxy.check()) return 0;
          if (is_range) break; // in a range all elements are of the same type
        }
        if (!is_range) assert(i == obj_size);
      }
      return obj_ptr;
    }

    static void construct(
      PyObject* obj_ptr,
      boost::python::converter::rvalue_from_python_stage1_data* data)
    {
      using namespace boost::python;
      handle<> obj_iter(PyObject_GetIter(obj_ptr));
      void* storage = (
        (converter::rvalue_from_python_storage<ContainerType>*)
          data)->storage.bytes;
      new (storage) ContainerType();
      data->convertible = storage;
      ContainerType& result = *((ContainerType*)storage);
      std::size_t i=0;
      for(;;i++) {
        handle<> py_elem_hdl(allow_null(PyIter_Next(obj_iter.get())));
        if (PyErr_Occurred()) throw_error_already_set();
        if (!py_elem_hdl.get()) break; // end of iteration
        object py_elem_obj(py_elem_hdl);
        extract<container_element_type> elem_proxy(py_elem_obj);
        ConversionPolicy::set_value(result, i, elem_proxy());
      }
      ConversionPolicy::assert_size(boost::type<ContainerType>(), i);
    }
  };

  template <typename ContainerType, typename ConversionPolicy>
  struct tuple_mapping
  {
    tuple_mapping() {
      boost::python::to_python_converter<
        ContainerType,
        to_tuple<ContainerType> >();
      from_python_sequence<
        ContainerType,
        ConversionPolicy>();
    }
  };

  template <typename ContainerType>
  struct tuple_mapping_fixed_size
  {
    tuple_mapping_fixed_size() {
      tuple_mapping<
        ContainerType,
        fixed_size_policy>();
    }
  };

  template <typename ContainerType>
  struct tuple_mapping_fixed_capacity
  {
    tuple_mapping_fixed_capacity() {
      tuple_mapping<
        ContainerType,
        fixed_capacity_policy>();
    }
  };

}}} // namespace scitbx::boost_python::container_conversions

#endif // SCITBX_BOOST_PYTHON_CONTAINER_CONVERSIONS_H
